from datetime import datetime
from pydantic import BaseModel


class InvoiceUploadHistoryBase(BaseModel):
    id: int
    invoice_id: str
    old_file_url: str
    new_file_url: str
    action_date: datetime

    model_config = {"from_attributes": True}


class PurchaseOrderUploadHistoryBase(BaseModel):
    id: int
    po_id: str
    old_file_url: str
    new_file_url: str
    action_date: datetime

    model_config = {"from_attributes": True}