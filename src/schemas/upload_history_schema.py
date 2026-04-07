"""module: upload_history_schema.py"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class InvoiceUploadHistoryBase(BaseModel):
    """Pydantic model representing the base structure of an invoice upload history record. This model includes fields for the unique identifier of the upload history record, the associated invoice ID, the old file URL before the update, the new file URL after the update, and the date and time when the action was performed. The model serves as a base for representing the history of file uploads related to invoices, allowing for tracking changes to invoice files over time and providing a structured format for storing and validating this information within the system."""

    id: int
    invoice_id: str
    old_file_url: str
    new_file_url: str
    action_date: datetime

    model_config = ConfigDict(from_attributes=True)


class PurchaseOrderUploadHistoryBase(BaseModel):
    """Pydantic model representing the base structure of a purchase order upload history record. This model includes fields for the unique identifier of the upload history record, the associated purchase order ID, the old file URL before the update, the new file URL after the update, and the date and time when the action was performed. The model serves as a base for representing the history of file uploads related to purchase orders, allowing for tracking changes to purchase order files over time and providing a structured format for storing and validating this information within the system."""

    id: int
    po_id: str
    old_file_url: str
    new_file_url: str
    action_date: datetime

    model_config = ConfigDict(from_attributes=True)
