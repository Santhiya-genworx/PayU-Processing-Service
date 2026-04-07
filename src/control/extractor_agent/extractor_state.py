"""Module defining the AgentState TypedDict for the extractor agent graph. This module provides a structured definition of the state used by the agents in the graph, including fields for raw text, file type, base64-encoded image data, confidence score, document type, detected document type, and the extracted data for both invoices and purchase orders. The AgentState TypedDict allows for optional fields (total=False) to accommodate different stages of the graph execution where certain pieces of information may not yet be available. This structured state is essential for maintaining consistency and clarity in the data being processed by the various agents in the graph."""

from typing import TypedDict

from src.schemas.invoice_schema import InvoiceRequest
from src.schemas.purchase_order_schema import PurchaseOrderRequest


class AgentState(TypedDict, total=False):
    """TypedDict defining the structure of the agent state used in the extractor graph. This state includes fields for raw text, file type, base64-encoded image data, confidence score, document type, detected document type, and the extracted data for both invoices and purchase orders. The fields are optional (total=False) to allow for flexibility in the state during different stages of the graph execution. This structured state is essential for maintaining consistency and clarity in the data being processed by the various agents in the graph."""

    raw_text: str
    file_type: str
    base64_image: str | None
    confidence_score: float
    document_type: str
    detected_document_type: str
    invoice_data: InvoiceRequest
    po_data: PurchaseOrderRequest
