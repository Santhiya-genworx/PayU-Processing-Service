from datetime import date, datetime
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.schemas.vendor_schema import VendorBase


class InvoiceItemsBase(BaseModel):
    item_description: str = Field(..., min_length=1, max_length=255)
    quantity: int | None = Field(None, gt=0)
    unit_price: float | None = Field(None, gt=0)
    total_price: float = Field(..., gt=0)

    model_config = ConfigDict(from_attributes=True)


class InvoiceRequest(BaseModel):
    invoice_id: str = Field(..., min_length=1, max_length=50)
    vendor: VendorBase
    po_id: list[str] = Field(default_factory=list)

    invoice_date: date
    due_date: date

    invoice_items: list[InvoiceItemsBase] = Field(..., min_length=1)

    currency_code: str = Field(..., min_length=3, max_length=3)
    subtotal: float = Field(..., ge=0)
    tax_amount: float = Field(..., ge=0)
    discount_amount: float | None = Field(default=0, ge=0)
    total_amount: float = Field(..., ge=0)

    @model_validator(mode="after")
    def validate_invoice(self) -> Self:

        if self.due_date < self.invoice_date:
            raise ValueError("Due date cannot be before invoice date")

        subtotal_check_possible = True

        calculated_subtotal: float = 0.0

        for item in self.invoice_items:
            if item.quantity is None or item.unit_price is None:
                subtotal_check_possible = False
                break
            calculated_subtotal += item.quantity * item.unit_price

        if subtotal_check_possible and round(calculated_subtotal, 2) != round(self.subtotal, 2):
            raise ValueError("Subtotal mismatch with invoice items")

        expected_total = self.subtotal + self.tax_amount - (self.discount_amount or 0)

        if round(expected_total, 2) != round(self.total_amount, 2):
            raise ValueError("Total amount calculation mismatch")

        return self


class InvoiceAction(BaseModel):
    invoice_id: str
    mail_to: str | None = None
    mail_subject: str | None = None
    mail_body: str | None = None

    model_config = ConfigDict(from_attributes=True)

class InvoiceResponse(BaseModel):
    invoice_id: str
    vendor_id: int
    invoice_date: date
    due_date: date
    currency_code: str
    subtotal: Decimal
    tax_amount: Decimal
    discount_amount: Decimal | None
    total_amount: Decimal
    file_url: str
    created_at: datetime
    updated_at: datetime

    vendor: VendorBase
    invoice_items: list[InvoiceItemsBase]

    model_config = {"from_attributes": True}
