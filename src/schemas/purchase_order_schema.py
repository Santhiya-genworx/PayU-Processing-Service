from typing import List
from pydantic import BaseModel, Field, model_validator
from datetime import date
from src.schemas.vendor_schema import VendorBase

class OrderedItemsBase(BaseModel):
    item_description: str = Field(..., min_length=1, max_length=255)
    quantity: int = Field(..., gt=0)
    unit_price: float = Field(..., gt=0)
    total_price: float = Field(..., gt=0)

class PurchaseOrderRequest(BaseModel):
    po_id: str = Field(..., min_length=1, max_length=50)
    vendor: VendorBase
    gl_code: str = Field(..., min_length=1, max_length=20)
    ordered_items: List[OrderedItemsBase] = Field(..., min_items=1)
    currency_code: str = Field(..., min_length=3, max_length=3)
    total_amount: float = Field(..., ge=0)
    ordered_date: date

    @model_validator(mode="after")
    def validate_po(self):
        if self.total_amount <= 0:
            raise ValueError("PO total amount must be greater than zero")
        return self