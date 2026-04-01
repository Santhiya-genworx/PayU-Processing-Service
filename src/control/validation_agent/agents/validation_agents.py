from typing import Any
import json
import re

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from pydantic import SecretStr

from src.control.validation_agent.validation_state import AgentState, Decision
from src.core.config.settings import settings

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0,
    api_key=SecretStr(settings.groq_api_key),
)

def _get_po_map(pos: list[Any]) -> dict[str, Any]:
    return {po.po_id: po for po in pos}


def _invoice_pos(invoice: Any, po_map: dict[str, Any]) -> list[Any]:
    if not invoice.po_id:
        return []
    ids: list[str] = invoice.po_id if isinstance(invoice.po_id, list) else [invoice.po_id]
    return [po_map[pid] for pid in ids if pid in po_map]


def _to_str(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item.strip())
            elif isinstance(item, dict):
                parts.append(str(item))
        return " ".join(parts)
    return str(content)


def _scenario(invoices: list[Any], pos: list[Any]) -> str:
    ni, np = len(invoices), len(pos)
    if ni == 1 and np == 0:
        return "1 invoice, no PO"
    if ni == 1 and np == 1:
        return "1 invoice, 1 PO"
    if ni == 1 and np > 1:
        return f"1 invoice, {np} POs"
    if ni > 1 and np == 1:
        return f"{ni} invoices, 1 PO"
    return f"{ni} invoices, {np} POs"

def vendor_match_node(state: AgentState) -> dict[str, list[AIMessage]]:
    invoices = state.get("invoices", [])
    pos = state.get("pos", [])
    messages: list[AIMessage] = []

    if not pos:
        messages.append(AIMessage(content="No PO — vendor match skipped"))
        return {"messages": messages}

    po_map = _get_po_map(pos)

    for invoice in invoices:
        inv_v = invoice.vendor
        invoice_pos = _invoice_pos(invoice, po_map)

        for po in invoice_pos:
            po_v = po.vendor
            prefix = f"[INV {invoice.invoice_id} / PO {po.po_id}]"

            if inv_v.name != po_v.name or inv_v.email != po_v.email:
                messages.append(AIMessage(content=f"{prefix} VENDOR_MISMATCH"))
            elif inv_v.gst_number != po_v.gst_number:
                messages.append(AIMessage(content=f"{prefix} GST_MISMATCH"))
            else:
                messages.append(AIMessage(content=f"{prefix} VENDOR_OK"))

    return {"messages": messages}


async def line_item_match_agent(state: AgentState) -> dict[str, list[AIMessage]]:
    invoices = state.get("invoices", [])
    pos = state.get("pos", [])

    if not pos:
        return {"messages": [AIMessage(content="No PO — skipped")]}

    po_map = _get_po_map(pos)

    invoices_block = ""
    for inv in invoices:
        inv_items = ", ".join(i.item_description for i in inv.invoice_items)
        invoice_pos = _invoice_pos(inv, po_map)

        po_items = " | ".join(
            f"PO {po.po_id}: " + ", ".join(i.item_description for i in po.ordered_items)
            for po in invoice_pos
        )

        invoices_block += f"{inv.invoice_id}: {inv_items} | {po_items}\n"

    result = await llm.ainvoke(
        [
            SystemMessage(content="Match invoice items to PO items"),
            HumanMessage(content=invoices_block),
        ]
    )

    return {"messages": [AIMessage(content=str(result.content))]}


def price_check_node(state: AgentState) -> dict[str, list[AIMessage]]:
    invoices = state.get("invoices", [])
    messages: list[AIMessage] = []

    for invoice in invoices:
        for item in invoice.invoice_items:
            if item.quantity and item.unit_price:
                expected = round(item.quantity * item.unit_price, 2)
                if expected != round(item.total_price, 2):
                    messages.append(AIMessage(content="LINE_CALC_ERROR"))

    if not messages:
        messages.append(AIMessage(content="PRICE_OK"))

    return {"messages": messages}


def quantity_price_match_agent(state: AgentState) -> dict[str, list[AIMessage]]:
    invoices = state.get("invoices", [])
    pos = state.get("pos", [])
    messages: list[AIMessage] = []

    if not pos:
        return {"messages": [AIMessage(content="NO_PO")]}

    po_map = _get_po_map(pos)

    def _find_po_item(po: Any, desc: str) -> Any | None:
        for item in po.ordered_items:
            if item.item_description.lower().strip() == desc:
                return item
        return None

    for invoice in invoices:
        invoice_pos = _invoice_pos(invoice, po_map)

        for inv_item in invoice.invoice_items:
            desc = inv_item.item_description.lower().strip()

            po_item = None
            for po in invoice_pos:
                po_item = _find_po_item(po, desc)
                if po_item is not None:
                    break

            if po_item is None:
                messages.append(
                    AIMessage(
                        content=f"ITEM_NOT_IN_PO: '{inv_item.item_description}' not found in any linked PO"
                    )
                )
                continue

            inv_qty = inv_item.quantity
            po_qty = po_item.quantity

            if inv_qty is not None and po_qty is not None:
                if inv_qty > po_qty:
                    messages.append(
                        AIMessage(
                            content=(
                                f"OVER_INVOICED: '{inv_item.item_description}' "
                                f"invoiced qty {inv_qty} exceeds PO qty {po_qty}"
                            )
                        )
                    )
                elif inv_qty < po_qty:
                    messages.append(
                        AIMessage(
                            content=(
                                f"PARTIAL_DELIVERY: '{inv_item.item_description}' "
                                f"invoiced qty {inv_qty} is less than PO qty {po_qty}"
                            )
                        )
                    )
            inv_price = inv_item.unit_price
            po_price = po_item.unit_price

            if inv_price is not None and po_price is not None:
                if inv_price != po_price:
                    messages.append(
                        AIMessage(
                            content=(
                                f"UNIT_PRICE_MISMATCH: '{inv_item.item_description}' "
                                f"invoice price {inv_price} != PO price {po_price}"
                            )
                        )
                    )

    if not messages:
        messages.append(AIMessage(content="QTY_OK"))

    return {"messages": messages}

_DECISION_SYSTEM_PROMPT = """
You are an invoice validation decision agent. You will receive a list of validation
results produced by earlier specialist agents. Each result is a short message
describing what was checked and what was found.

Your job is to read ALL messages carefully and decide ONE of three outcomes:

- "approve"  → All checks passed. No issues found.
- "review"   → Minor issues that need human review but are not outright rejections.
- "reject"   → Hard failures that must not be approved.

Decision hierarchy (strict):
1. If ANY hard failure is present → "reject", regardless of other results.
2. If no hard failures but soft warnings exist → "review".
3. Only decide "approve" when every single check passed cleanly.

Important:
- Read the full sentence of each message for intent — do not just scan for keywords.
- Do NOT be influenced by message order. Read everything before deciding.
- A message saying "skipped" or "no PO" is neutral — not a pass or a failure.

Return ONLY a valid JSON object with no markdown fences, no preamble, no explanation:
{
  "status": "approve" | "review" | "reject",
  "confidence_score": <float 0.0–1.0>,
  "reasoning": "<one concise sentence>",
  "command": "<most critical issue found, or 'Approved' if approved>"
}
""".strip()

_MAIL_DRAFT_SYSTEM_PROMPT = """
You are a professional accounts payable coordinator drafting emails to vendors
about invoice discrepancies.

You will receive:
- The validation status: either "review" or "reject"
- A list of validation findings for the invoice

Read the findings carefully and draft a clear, professional, concise email to the
vendor. Use your own judgment on tone and content based on what the findings say —
do not rely on any fixed rules or keywords.

- Keep the email under 200 words.
- Always reference any invoice or PO IDs mentioned in the findings.
- Do not make up data that is not present in the findings.

Return ONLY a valid JSON object with no markdown fences, no preamble, no explanation:
{
  "mail_to": "vendor@example.com",
  "mail_subject": "<subject line>",
  "mail_body": "<full email body>"
}
""".strip()

def _parse_llm_decision(raw: str) -> dict[str, Any]:
    """
    Robustly extract the JSON decision from LLM output even when the model
    wraps it in markdown fences or adds stray commentary.
    """
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return {
        "status": "review",
        "confidence_score": 0.5,
        "reasoning": "Decision agent returned unparseable output — flagged for human review.",
        "command": "PARSE_ERROR",
    }


async def decision_agent(state: AgentState):
    print("Decision..")

    invoices     = state.get("invoices", [])
    pos          = state.get("pos", [])
    invoice      = invoices[0] if invoices else None
    po           = pos[0] if pos else None

    vendor_email = invoice.vendor.email if invoice else "vendor@example.com"
    vendor_name  = invoice.vendor.name if invoice else "Vendor"
    po_id        = po.po_id if po else "N/A"
    invoice_date = str(invoice.invoice_date) if invoice and invoice.invoice_date else "N/A"
    invoice_type = "SERVICE (no PO exists)" if po is None else "PRODUCT (PO exists)"

    previous_results = [m.content for m in state["messages"]]

    prompt = [
        SystemMessage(
            content=f"""
            You are an Accounts Payable automation decision agent.
            This invoice is of type: {invoice_type}

            You will receive validation messages from previous agents:
            - vendor validation (only if PO exists)
            - line item matching (only if PO exists)
            - price check
            - quantity and price validation (only if PO exists)

            For SERVICE invoices (no PO), only price check results will be present. This is expected and normal.

            Based on these, determine the final decision and populate ALL fields precisely.

            === DECISION RULES ===

            approve:
            - All validations passed with no issues
            - command: MUST be exactly "Invoice verified and approved for payment processing"
            - mail_to: MUST be null
            - mail_subject: MUST be null
            - mail_body: MUST be null
            - DO NOT generate any email for approve status under any circumstance

            review:
            - Minor mismatch or clarification needed (quantity diff, small price variance, description ambiguity)
            - command: Concise one-line issue summary with specifics
              e.g. "Quantity mismatch on item 1 (Dell Laptop XPS 15): PO qty=5, Invoice qty=4"
            - mail_to: MUST be set to vendor email
            - mail_subject and mail_body: MUST be populated

            reject:
            - Major mismatch (vendor fraud risk, large amount discrepancy, GST mismatch, missing items)
            - command: Concise one-line rejection reason
              e.g. "Vendor GST mismatch and total overbilled by INR 95,000 - invoice rejected"
            - mail_to: MUST be set to vendor email
            - mail_subject and mail_body: MUST be populated

            === command FIELD RULES ===
            - MUST never be null or empty for any status
            - Always specific and human-readable — describe the actual problem found
            - Never use generic phrases like "make decision", "process invoice", or "review needed"
            - If multiple issues, summarise the most critical one and append "+ N more issues"
              e.g. "Quantity mismatch on item 1 (Dell Laptop): PO=5 vs Invoice=4 + 1 more issue"

            === EMAIL RULES ===
            - Email fields (mail_to, mail_subject, mail_body) MUST be null for approve
            - Email fields MUST be populated for review and reject
            - Use hyphen (-) instead of em dash (—) everywhere in subject and body
            - Use * for bullet points instead of special unicode bullet characters
            - In mail_body, use literal \\n for line breaks, no special characters

            === EMAIL FORMAT (review / reject only) ===

            Subject format: "Re: Invoice {{invoice_id}} against PO {{po_id}} - {{short issue type}}"
            For service invoices with no PO: "Re: Invoice {{invoice_id}} - {{short issue type}}"

            Body structure:
            Dear {{Vendor Name}} Team,\\n\\n
            We are writing with reference to Invoice No. {{invoice_id}} dated {{invoice_date}}.\\n\\n
            [If PO exists, add: submitted against Purchase Order No. {{po_id}}.]\\n\\n
            Upon review, our Accounts Payable team has identified the following discrepancy(ies):\\n\\n
            * [Issue 1 - specific field, expected value vs received value]\\n
            * [Issue 2 if applicable]\\n\\n
            [For review]: Kindly review the above and resubmit a corrected invoice or provide written clarification within 3 business days.\\n\\n
            [For reject]: As the discrepancies are material, we are unable to process this invoice. Please issue a revised invoice addressing all points above.\\n\\n
            For any queries, please contact our AP team at accounts@company.com.\\n\\n
            Warm regards,\\n
            Accounts Payable Team\\n
            PayU

            === confidence_score RULES ===
            1.00 - all validations pass
            0.85 - 1 soft warning or minor mismatch
            0.70 - 1 hard fail
            0.55 - 2 hard fails
            0.40 - 3 or more hard fails or vendor identity mismatch
            """
        ),
        HumanMessage(
            content=f"""
            Invoice Type: {invoice_type}
            Vendor Name:  {vendor_name}
            Vendor Email: {vendor_email}
            Invoice ID:   {invoice.invoice_id if invoice else "N/A"}
            Invoice Date: {invoice_date}
            PO ID:        {po_id}

            Validation Messages:
            {chr(10).join(f"  - {msg}" for msg in previous_results)}

            IMPORTANT REMINDERS:
            - command must NEVER be null
            - If status is approve, mail_to/mail_subject/mail_body MUST be null — do not generate email
            - If status is review or reject, mail_to/mail_subject/mail_body MUST be populated
            - This is a {invoice_type} invoice, so {"no PO reference is expected" if po is None else f"PO ID is {po_id}"}

            Return the final structured decision.
            """
        )
    ]

    result   = await llm.with_structured_output(Decision).ainvoke(prompt)
    decision = result.model_dump()

    return {"output": decision}