from datetime import date, datetime
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.schemas.vendor_schema import VendorBase


class OrderedItemsBase(BaseModel):
    item_description: str = Field(..., min_length=1, max_length=255)
    quantity: int = Field(..., gt=0)
    unit_price: float = Field(..., gt=0)
    total_price: float = Field(..., gt=0)

    model_config = ConfigDict(from_attributes=True)


class PurchaseOrderRequest(BaseModel):
    po_id: str = Field(..., min_length=1, max_length=50)
    vendor: VendorBase
    gl_code: str = Field(..., min_length=1, max_length=20)

    ordered_items: list[OrderedItemsBase] = Field(..., min_length=1)

    currency_code: str = Field(..., min_length=3, max_length=3)
    total_amount: float = Field(..., ge=0)
    ordered_date: date

    @model_validator(mode="after")
    def validate_po(self) -> Self:
        if self.total_amount <= 0:
            raise ValueError("PO total amount must be greater than zero")
        return self

    model_config = ConfigDict(from_attributes=True)

class PurchaseOrderResponse(BaseModel):
    po_id: str
    vendor_id: int
    gl_code: str
    total_amount: Decimal
    currency_code: str
    ordered_date: date
    file_url: str
    status: str
    created_at: datetime
    updated_at: datetime

    vendor: VendorBase
    ordered_items: list[OrderedItemsBase]

    model_config = {"from_attributes": True}
