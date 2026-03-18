from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_groq import ChatGroq
from src.core.config.settings import settings
from src.control.validation_agent.state import AgentState, Decision

llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0,
    api_key=settings.groq_api_key
)

def vendor_match_node(state: AgentState):
    print("Vendor match..")

    inv_vendor = state["invoice"].vendor
    po_vendor = state["po"].vendor

    if inv_vendor.name != po_vendor.name or inv_vendor.email != po_vendor.email:
        return {"messages": [AIMessage(content="Vendor name or email mismatch")]}

    if inv_vendor.gst_number != po_vendor.gst_number:
        return {"messages": [AIMessage(content="Vendor GST mismatch between PO and Invoice")]}

    return {"messages": [AIMessage(content="Vendor validation passed")]}

async def line_item_match_node(state: AgentState):
    print("Line item match..")

    po_items  = [i.item_description for i in state["po"].ordered_items]
    inv_items = [i.item_description for i in state["invoice"].invoice_items]

    messages = [
        SystemMessage(content="Match invoice items with PO items even if wording differs."),
        HumanMessage(content=f"PO items: {po_items}\nInvoice items: {inv_items}"),
    ]

    result = await llm.ainvoke(messages)
    return {"messages": [AIMessage(content=f"Line item matching result: {result.content}")]}

def price_check_node(state: AgentState):
    print("Price check..")

    invoice  = state["invoice"]
    messages = []

    for item in invoice.invoice_items:
        # Service items: only total_price matters, skip calculation check silently
        if item.quantity is None or item.unit_price is None:
            continue  # ← was appending a message here, now silent

        expected = round(item.quantity * item.unit_price, 2)

        if round(expected, 2) != round(item.total_price, 2):
            messages.append(
                AIMessage(
                    content=f"Calculation error for '{item.item_description}': "
                            f"{item.quantity} x {item.unit_price} = {expected}, "
                            f"but total_price is {item.total_price}"
                )
            )

    if not messages:
        messages.append(AIMessage(content="Per-line price calculation check passed"))

    return {"messages": messages}

def quantity_price_match_node(state: AgentState):
    print("Quantity price match..")

    invoice  = state["invoice"]
    po       = state["po"]
    messages = []

    po_items  = po.ordered_items if po else []
    inv_items = invoice.invoice_items

    if po and len(po_items) != len(inv_items):
        messages.append(
            AIMessage(
                content=f"Line item count mismatch: PO has {len(po_items)}, Invoice has {len(inv_items)}"
            )
        )
        return {"messages": messages}

    for idx, (po_item, inv_item) in enumerate(zip(po_items, inv_items), start=1):
        is_service_item = inv_item.quantity is None and inv_item.unit_price is None

        if not is_service_item:
            # Quantity check
            if inv_item.quantity is not None and po_item.quantity is not None:
                if inv_item.quantity != po_item.quantity:
                    messages.append(AIMessage(
                        content=f"Quantity mismatch for item {idx} ({inv_item.item_description}): "
                                f"PO={po_item.quantity}, Invoice={inv_item.quantity}"
                    ))

            # Unit price check
            if inv_item.unit_price is not None and po_item.unit_price is not None:
                if round(inv_item.unit_price, 2) != round(po_item.unit_price, 2):
                    messages.append(AIMessage(
                        content=f"Unit price mismatch for item {idx} ({inv_item.item_description}): "
                                f"PO={po_item.unit_price}, Invoice={inv_item.unit_price}"
                    ))

        # Total price check always applies (service or not)
        if po and inv_item.total_price is not None and po_item.total_price is not None:
            if round(inv_item.total_price, 2) != round(po_item.total_price, 2):
                messages.append(AIMessage(
                    content=f"Total price mismatch for item {idx} ({inv_item.item_description}): "
                            f"PO={po_item.total_price}, Invoice={inv_item.total_price}"
                ))

    # Subtotal check
    inv_totals = [i.total_price for i in inv_items if i.total_price is not None]
    if inv_totals:
        calculated_subtotal = sum(inv_totals)
        if round(calculated_subtotal, 2) != round(invoice.subtotal, 2):
            messages.append(AIMessage(
                content=f"Subtotal mismatch: calculated {calculated_subtotal}, invoice shows {invoice.subtotal}"
            ))

    # Final amount check
    if invoice.subtotal is not None and invoice.tax_amount is not None:
        expected_total = invoice.subtotal + invoice.tax_amount - (invoice.discount_amount or 0)
        if round(expected_total, 2) != round(invoice.total_amount, 2):
            messages.append(AIMessage(
                content=f"Total amount mismatch: expected {expected_total}, invoice shows {invoice.total_amount}"
            ))

    if not messages:
        messages.append(AIMessage(content="Quantity, unit price, subtotal, and tax validation passed"))

    return {"messages": messages}
async def decision_agent(state: AgentState):
    print("Decision..")

    invoice      = state["invoice"]
    vendor_email = invoice.vendor.email
    vendor_name  = invoice.vendor.name
    po           = state.get("po")
    po_id        = po.po_id if po else "N/A"
    invoice_date = str(invoice.invoice_date) if invoice.invoice_date else "N/A"
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
            Invoice ID:   {invoice.invoice_id}
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