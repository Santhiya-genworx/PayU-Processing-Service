from fastapi import HTTPException
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import ValidationError
from src.core.config.settings import settings
from src.control.state import AgentState
from src.schemas.invoice_schema import InvoiceRequest
from src.schemas.purchase_order_schema import PurchaseOrderRequest
from langchain_google_genai import ChatGoogleGenerativeAI

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.7,
    api_key=settings.gemini_api_key
)

async def detect_document_type(state: AgentState) -> str:
    """ Detect what type of document this actually is."""

    try:
        messages = [
            SystemMessage(
                content="""
                    You are a document classifier.
                    Classify the given document as either "invoice" or "purchase_order".
                    
                    Rules:
                    - If the document title/header says "PURCHASE ORDER", "PO", "ORDER CONFIRMATION" → return "purchase_order"
                    - If the document title/header says "INVOICE", "TAX INVOICE", "BILL" → return "invoice"
                    - If the document doesn't belong to above → return "unknown"
                    - Look at the PRIMARY identifier field:
                        - Has "PO #", "PO Number", "Purchase Order No" as main ID → "purchase_order"
                        - Has "Invoice No", "Invoice #", "Bill No" as main ID → "invoice"
                    
                    Return ONLY one word: either "invoice" or "purchase_order" or "unknown". Nothing else.
                """
            ),
            HumanMessage(
                content=f"Classify this document:\n\n{state["raw_text"]}"
            )
        ]
        response = await llm.ainvoke(messages)
        return {
            "detected_document_type": response.content.strip().lower()
        }
    except Exception as err:
        raise HTTPException(status_code=400, detail=str(err))

def format_validation_errors(error: ValidationError) -> str:
    """Convert pydantic validation errors into a polite, readable message."""

    messages = []
    for err in error.errors():
        field_path = " → ".join(str(loc) for loc in err["loc"])
        error_type = err["type"]
        raw_msg = err["msg"]

        if error_type == "missing":
            messages.append(f"• **{field_path}** is required but was not found in the document.")
        elif error_type == "string_too_short":
            messages.append(f"• **{field_path}** is too short or appears incomplete.")
        elif error_type == "string_too_long":
            messages.append(f"• **{field_path}** exceeds the allowed length.")
        elif error_type == "value_error":
            messages.append(f"• **{field_path}**: {raw_msg.replace('Value error, ', '')}")
        elif error_type in ("int_parsing", "float_parsing"):
            messages.append(f"• **{field_path}** could not be read as a valid number.")
        elif error_type == "date_parsing":
            messages.append(f"• **{field_path}** has an unrecognizable date format.")
        elif "pattern" in error_type:
            messages.append(f"• **{field_path}** does not match the expected format.")
        else:
            messages.append(f"• **{field_path}**: {raw_msg}")

    error_list = "\n".join(messages)
    return (
        "We couldn't fully process this document due to the following issues:\n\n"
        f"{error_list}\n\n"
        "Please review the document and ensure all required fields are present and correctly formatted."
    )

async def text_extractor(state: AgentState):
    """
    Agent which reads text input and converts into structured json
    """

    print("Text Extractor...")
    try:
        document_type = state["document_type"]
        detected_document_type = state["detected_document_type"]

        if detected_document_type == "unknown":
            raise HTTPException(status_code=400, detail=f"Unknown file type. Kindly upload correct {document_type}")

        if document_type != detected_document_type:
            raise HTTPException(status_code=400, detail=f"Expected {document_type}. But got {detected_document_type}")

        if document_type == "invoice":
            doc_instructions = """
                You are extracting data from an INVOICE document ONLY.
                
                STRICT RULES:
                - An invoice MUST contain: invoice_id, invoice_date, due_date, subtotal, tax_amount, total_amount, and line items.
                - A Purchase Order (PO) is NOT an invoice. If the document is a PO (contains "Purchase Order", "PO Number", "Ordered Date" but no invoice_id or invoice_date), do NOT extract it — return nothing and let validation fail.
                - Do NOT use po_id as invoice_id. These are different fields.
                - po_id is OPTIONAL in an invoice and should only be filled if the invoice explicitly references a Purchase Order number.
                - If invoice_id is missing or the document is clearly not an invoice, do not hallucinate values.
            """
        else:
            doc_instructions = """
                You are extracting data from a PURCHASE ORDER (PO) document ONLY.
                
                STRICT RULES:
                - A PO MUST contain: po_id, ordered_date, ordered_items, vendor info, and total_amount.
                - An Invoice is NOT a Purchase Order. If the document is an invoice (contains "invoice_id", "invoice_date", "due_date"), do NOT extract it — return nothing and let validation fail.
                - Do NOT use invoice_id as po_id. These are different fields.
                - If po_id is missing or the document is clearly not a PO, do not hallucinate values.
            """

        messages = [
            SystemMessage(
                content=f"""
                    You are a precise financial document extractor.
                    {doc_instructions}
                    Extract data strictly according to the provided schema.
                    Do NOT hallucinate or guess missing values.
                    Do NOT substitute one field for another (e.g., do not use po_id where invoice_id is expected).
                """
            ),
            HumanMessage(
                content=f"""
                    The user expects this to be a **{document_type.upper()}** document.
                    If the document is NOT a {document_type}, do not attempt extraction.
                    Document content:
                    {state["raw_text"]}
                """
            )
        ]

        if state["document_type"] == "invoice":
            llm_invoice = llm.with_structured_output(InvoiceRequest)
            try:
                response = await llm_invoice.ainvoke(messages)
                return {"invoice_data": response.model_dump()}
            except ValidationError as ve:
                raise HTTPException(status_code=400, detail=format_validation_errors(ve))
        else:
            llm_po = llm.with_structured_output(PurchaseOrderRequest)
            try:
                response = await llm_po.ainvoke(messages)
                return {"po_data": response.model_dump()}
            except ValidationError as ve:
                raise HTTPException(status_code=400, detail=format_validation_errors(ve))

    except Exception as err:
        raise Exception(f"{str(err)}")

async def vision_extractor(state: AgentState):
    """
    Agent which extracts raw text from an image using vision model
    """

    print("Vision Extractor...")
    try:
        messages = [
            SystemMessage(
                content="""
                    You are a financial document OCR assistant.
                    Extract all readable text from the image.
                    Only return plain text.
                    Do NOT generate JSON, do NOT attempt tool calls.
                    Do not summarize or hallucinate.
                """
            ),
            HumanMessage(
                content=[
                    {
                        "type": "text",
                        "text": "Extract all readable text from this document image."
                    },
                    {
                        "type": "image_url",
                        "image_url": { "url": f"data:image/jpeg;base64,{state["base64_image"]}" }
                    }
                ]
            )
        ]

        response = await llm.ainvoke(messages)
        return {
            "raw_text": response.content.strip()
        }

    except Exception as err:
        raise Exception(f"Vision extraction failed: {str(err)}")