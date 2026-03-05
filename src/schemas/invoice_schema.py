from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, model_validator
from datetime import date
from src.schemas.vendor_schema import VendorBase

class InvoiceItemsBase(BaseModel):
    item_description: str = Field(..., min_length=1, max_length=255)
    quantity: int = Field(..., gt=0)
    unit_price: float = Field(..., gt=0)
    total_price: float = Field(..., gt=0)

class InvoiceRequest(BaseModel):
    invoice_id: str = Field(..., min_length=1, max_length=50)
    vendor: VendorBase
    po_id: str = Field(..., min_length=1)
    invoice_date: date
    due_date: date
    invoice_items: List[InvoiceItemsBase] = Field(..., min_items=1)
    currency_code: str = Field(..., min_length=3, max_length=3)
    subtotal: float = Field(..., ge=0)
    tax_amount: float = Field(..., ge=0)
    discount_amount: Optional[float] = Field(default=0, ge=0)
    total_amount: float = Field(..., ge=0)

    @model_validator(mode="after")
    def validate_invoice(self):
        if self.due_date < self.invoice_date:
            raise ValueError("Due date cannot be before invoice date")

        calculated_subtotal = sum(item.quantity * item.unit_price for item in self.invoice_items)
        if round(calculated_subtotal, 2) != round(self.subtotal, 2):
            raise ValueError("Subtotal mismatch with invoice items")

        expected_total = self.subtotal + self.tax_amount - (self.discount_amount or 0)
        if round(expected_total, 2) != round(self.total_amount, 2):
            raise ValueError("Total amount calculation mismatch")

        return self
