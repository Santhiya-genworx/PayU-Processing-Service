from typing import TypedDict
from src.schemas.invoice_schema import InvoiceRequest
from src.schemas.purchase_order_schema import PurchaseOrderRequest

class AgentState(TypedDict, total=False):
    raw_text: str
    file_type: str
    base64_image: str
    confidence_score: float
    document_type: str
    detected_document_type: str
    invoice_data: InvoiceRequest
    po_data: PurchaseOrderRequest