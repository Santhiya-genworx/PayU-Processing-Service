"""Module defining the validation agents for processing invoices and purchase orders. This module includes functions that perform various validation checks on the extracted data, such as vendor matching, line item matching, price checks, and quantity-price validation. Each function takes the current agent state as input and produces a list of AIMessage objects that describe the results of the validation checks. The module also includes a decision agent that synthesizes the results from all validation agents to make a final decision on whether to approve, review, or reject the invoice. The decision agent uses a structured prompt to guide the language model in making an informed decision based on the validation results, and it returns a structured output containing the decision status, confidence score, reasoning, and any necessary commands or email drafts for communication with vendors.  This modular design allows for clear separation of concerns, where each validation agent focuses on a specific aspect of the invoice processing, and the decision agent integrates these insights to drive the overall workflow effectively."""

from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from pydantic import SecretStr

from src.config.settings import settings
from src.control.validation_agent.validation_state import AgentState, Decision
from src.observability.logging.logging_config import logger
from src.schemas.graph_output_schema import GraphResult, MatchingOutput

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0,
    api_key=SecretStr(settings.groq_api_key),
)


def _get_po_map(pos: list[Any]) -> dict[str, Any]:
    """Helper function to create a mapping of purchase order IDs to their corresponding data. This function takes a list of purchase orders and constructs a dictionary where the keys are the purchase order IDs and the values are the purchase order data. This mapping allows for efficient lookup of purchase order information based on their IDs, which is essential for various validation checks that require referencing the associated purchase orders for a given invoice. Args:   pos (list[Any]): A list of purchase order objects, each containing an ID and associated data. Returns:    A dictionary mapping purchase order IDs (str) to their corresponding data (Any)."""
    return {po.po_id: po for po in pos}


def _invoice_pos(invoice: Any, po_map: dict[str, Any]) -> list[Any]:
    """Helper function to retrieve the purchase orders associated with a given invoice based on the purchase order IDs listed in the invoice. This function checks the 'po_id' field in the invoice, which may contain a single ID or a list of IDs, and uses the provided mapping of purchase order IDs to retrieve the corresponding purchase order data. The function returns a list of purchase orders that are linked to the invoice, allowing for further validation checks that require access to the details of these associated purchase orders. Args:   invoice (Any): The invoice object that contains a 'po_id' field referencing associated purchase orders. po_map (dict[str, Any]): A dictionary mapping purchase order IDs to their corresponding data. Returns:    A list of purchase order data objects that are associated with the given invoice based on the 'po_id' references."""
    if not invoice.po_id:
        return []
    ids: list[str] = invoice.po_id if isinstance(invoice.po_id, list) else [invoice.po_id]
    return [po_map[pid] for pid in ids if pid in po_map]


def vendor_match_node(state: AgentState) -> dict[str, list[AIMessage]]:
    """Agent function to perform vendor matching validation between invoices and purchase orders. This function checks if the vendor information (name, email, GST number) in the invoice matches the corresponding information in the associated purchase orders. It generates AIMessage objects that indicate whether there is a vendor mismatch, GST mismatch, or if the vendor information is consistent across the invoice and purchase orders. If there are no associated purchase orders, it generates a message indicating that the vendor match was skipped. The results of these checks are returned in a dictionary format containing a list of AIMessage objects that describe the validation outcomes for the vendor matching process. Args:   state (AgentState): The current state of the agent, which includes the extracted invoice and purchase order data needed for validation. Returns:    A dictionary containing a list of AIMessage objects that describe the results of the vendor matching validation."""
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
    """Agent function to perform line item matching validation between invoices and purchase orders. This function checks if the line items listed in the invoice match the corresponding items in the associated purchase orders based on their descriptions. It generates AIMessage objects that indicate whether each invoice item is found in the purchase orders, and if so, whether there are any discrepancies in quantity or unit price. If there are no associated purchase orders, it generates a message indicating that the line item match was skipped. The results of these checks are returned in a dictionary format containing a list of AIMessage objects that describe the validation outcomes for the line item matching process. Args:   state (AgentState): The current state of the agent, which includes the extracted invoice and purchase order data needed for validation. Returns:    A dictionary containing a list of AIMessage objects that describe the results of the line item matching validation."""
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
    """Agent function to perform price validation checks on invoice line items. This function calculates the expected total price for each line item based on the quantity and unit price, and compares it to the total price listed in the invoice. It generates AIMessage objects that indicate whether there is a line calculation error (where the expected total does not match the listed total) or if the price is correct. The results of these checks are returned in a dictionary format containing a list of AIMessage objects that describe the validation outcomes for the price check process. Args:   state (AgentState): The current state of the agent, which includes the extracted invoice data needed for validation. Returns:    A dictionary containing a list of AIMessage objects that describe the results of the price validation checks."""
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
    """Agent function to perform quantity and price validation checks between invoices and purchase orders. This function compares the quantities and unit prices of line items in the invoice against the corresponding items in the associated purchase orders. It generates AIMessage objects that indicate whether there are any over-invoicing issues (where the invoiced quantity exceeds the PO quantity), partial delivery issues (where the invoiced quantity is less than the PO quantity), or unit price mismatches. If there are no associated purchase orders, it generates a message indicating that the quantity and price match was skipped. The results of these checks are returned in a dictionary format containing a list of AIMessage objects that describe the validation outcomes for the quantity and price matching process. Args:   state (AgentState): The current state of the agent, which includes the extracted invoice and purchase order data needed for validation. Returns:    A dictionary containing a list of AIMessage objects that describe the results of the quantity and price validation checks."""
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


async def decision_agent(state: AgentState) -> GraphResult:
    """Agent function to synthesize validation results and make a final decision on whether to approve, review, or reject an invoice. This function reads the messages produced by previous validation agents, applies a strict decision hierarchy to determine the overall status of the invoice, and generates a structured output containing the decision status, confidence score, reasoning, and any necessary commands or email drafts for communication with vendors. The decision is based on the presence of hard failures (which lead to rejection), soft warnings (which lead to review), or a clean pass (which leads to approval). The function uses a structured prompt to guide the language model in making an informed decision based on the validation results. Args:   state (AgentState): The current state of the agent, which includes the messages from previous validation agents that describe the outcomes of various checks performed on the invoice. Returns:    A dictionary containing the final decision status ("approve", "review", or "reject"), a confidence score, reasoning for the decision, and any commands or email drafts if applicable."""
    logger.info("Decision..")

    invoices = state.get("invoices", [])
    pos = state.get("pos", [])
    invoice = invoices[0] if invoices else None
    po = pos[0] if pos else None

    vendor_email = invoice.vendor.email if invoice else "vendor@example.com"
    vendor_name = invoice.vendor.name if invoice else "Vendor"
    po_id = po.po_id if po else "N/A"
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
        ),
    ]

    result = await llm.with_structured_output(Decision).ainvoke(prompt)
    decision: Decision = Decision.model_validate(result)

    result = GraphResult(output=MatchingOutput.model_validate(decision))
    return result
