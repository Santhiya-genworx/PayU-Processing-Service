"""module: purchase_order_schema.py"""

from datetime import date, datetime
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.schemas.vendor_schema import VendorBase


class OrderedItemsBase(BaseModel):
    """Pydantic model representing the base structure of an ordered item within a purchase order. This model includes fields for item description, quantity, unit price, and total price. The item_description field is a required string with a minimum length of 1 and a maximum length of 255 characters. The quantity field is a required integer that must be greater than 0. The unit_price field is a required float that must be greater than 0. The total_price field is a required float that must be greater than 0. This model serves as the basis for defining the structure of individual line items within a purchase order, allowing for validation of the data related to each item and ensuring that all necessary information is provided when creating or processing purchase orders."""

    item_description: str = Field(..., min_length=1, max_length=255)
    quantity: int = Field(..., gt=0)
    unit_price: float = Field(..., gt=0)
    total_price: float = Field(..., gt=0)

    model_config = ConfigDict(from_attributes=True)


class PurchaseOrderRequest(BaseModel):
    """Pydantic model representing the structure of a purchase order request. This model includes fields for purchase order ID, vendor information, GL code, a list of ordered items, currency code, total amount, and ordered date. The po_id is a required string with a minimum length of 1 and a maximum length of 50 characters. The vendor field is an instance of the VendorBase model, which contains the necessary information about the vendor associated with the purchase order. The gl_code field is a required string that represents the general ledger code for accounting purposes. The ordered_items field is a required list of OrderedItemsBase instances, ensuring that at least one item is included in the purchase order. The currency_code is a required string that must be exactly 3 characters long (e.g., "USD", "EUR"). The total_amount field is a required float that must be greater than 0, representing the total financial value of the purchase order. The ordered_date field is a required date value that represents when the purchase order was placed. This model serves as the structure for incoming purchase order data when creating or processing purchase orders within the system, providing validation to ensure that all necessary information is included and correctly formatted."""

    po_id: str = Field(..., min_length=1, max_length=50)
    vendor: VendorBase
    gl_code: str = Field(..., min_length=1, max_length=20)

    ordered_items: list[OrderedItemsBase] = Field(..., min_length=1)

    currency_code: str = Field(..., min_length=3, max_length=3)
    total_amount: float = Field(..., ge=0)
    ordered_date: date

    @model_validator(mode="after")
    def validate_po(self) -> Self:
        """Custom validation logic for the PurchaseOrderRequest model. This method performs checks to ensure the integrity and consistency of the purchase order data. It calculates the total amount based on the provided ordered items by multiplying the quantity and unit price for each item and summing them up. If the calculated total does not match the provided total_amount (after rounding to 2 decimal places), it raises a ValueError indicating a mismatch. Additionally, it checks that the total_amount is greater than zero, raising a ValueError if this condition is violated. If all validations pass successfully, it returns the validated instance of PurchaseOrderRequest."""
        if self.total_amount <= 0:
            raise ValueError("PO total amount must be greater than zero")
        return self

    model_config = ConfigDict(from_attributes=True)


class PurchaseOrderResponse(BaseModel):
    """Pydantic model representing the response structure for a purchase order. This model includes fields for purchase order ID, vendor ID, GL code, total amount, currency code, ordered date, file URL, status, timestamps for creation and updates, vendor information (as a VendorBase instance), and a list of ordered items (as OrderedItemsBase instances). The po_id is a string that uniquely identifies the purchase order. The vendor_id is an integer that references the associated vendor. The gl_code is a string that represents the general ledger code for accounting purposes. The total_amount is a decimal field that represents the total financial value of the purchase order. The currency_code is a string that indicates the currency used in the purchase order (e.g., "USD", "EUR"). The ordered_date is a date field that represents when the purchase order was placed. The file_url is a string that provides a link to the file associated with the purchase order. The status is a string that indicates the current state of the purchase order (e.g., "pending", "completed", "cancelled"). The created_at and updated_at fields are datetime fields that automatically record when the purchase order record was created and last updated. The vendor field contains detailed information about the vendor associated with the purchase order, while the ordered_items field contains a list of items included in the purchase order, each with its own description, quantity, unit price, and total price. This model serves as a comprehensive representation of a purchase order response that can be returned in API responses or used within the application logic to display or process purchase order data."""

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

    model_config = ConfigDict(from_attributes=True)
