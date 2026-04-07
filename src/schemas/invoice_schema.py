"""module: invoice_schema.py"""

from datetime import date, datetime
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.schemas.vendor_schema import VendorBase


class InvoiceItemsBase(BaseModel):
    """Pydantic model representing the base structure of an invoice item. This model includes fields for item description, quantity, unit price, and total price. The item_description field is a required string with a minimum length of 1 and a maximum length of 255 characters. The quantity field is an optional integer that must be greater than 0 if provided. The unit_price field is an optional float that must be greater than 0 if provided. The total_price field is a required float that must be greater than 0. This model serves as the basis for defining the structure of individual items within an invoice, allowing for validation of the data related to each item and ensuring that all necessary information is provided when creating or processing invoices."""

    item_description: str = Field(..., min_length=1, max_length=255)
    quantity: int | None = Field(None, gt=0)
    unit_price: float | None = Field(None, gt=0)
    total_price: float = Field(..., gt=0)

    model_config = ConfigDict(from_attributes=True)


class InvoiceRequest(BaseModel):
    """Pydantic model representing the structure of an invoice request. This model includes fields for invoice ID, vendor information, associated purchase order IDs, invoice date, due date, a list of invoice items, currency code, subtotal, tax amount, discount amount, and total amount. The invoice_id is a required string with a minimum length of 1 and a maximum length of 50 characters. The vendor field is an instance of the VendorBase model, which contains the necessary information about the vendor associated with the invoice. The po_id field is a list of strings representing the IDs of purchase orders related to this invoice, with a default empty list if not provided. The invoice_date and due_date fields are required date values that represent when the invoice was issued and when it is due for payment, respectively. The invoice_items field is a required list of InvoiceItemsBase instances, ensuring that at least one item is included in the invoice. The currency_code is a required string that must be exactly 3 characters long (e.g., "USD", "EUR"). The subtotal, tax_amount, discount_amount (optional), and total_amount fields are required float values that represent the financial details of the invoice. This model serves as the structure for incoming invoice data when creating or processing invoices within the system, providing validation to ensure that all necessary information is included and correctly formatted."""

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
        """Custom validation logic for the InvoiceRequest model. This method performs several checks to ensure the integrity and consistency of the invoice data. It first checks that the due date is not before the invoice date, raising a ValueError if this condition is violated. Next, it calculates the subtotal based on the provided invoice items by multiplying the quantity and unit price for each item and summing them up. If any item has a missing quantity or unit price, it skips the subtotal check. If the calculated subtotal does not match the provided subtotal (after rounding to 2 decimal places), it raises a ValueError indicating a mismatch. Finally, it calculates the expected total amount by adding the subtotal and tax amount, then subtracting any discount amount. If this expected total does not match the provided total amount (after rounding to 2 decimal places), it raises a ValueError indicating a mismatch in total amount calculation. If all validations pass successfully, it returns the validated instance of InvoiceRequest."""

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
    """Pydantic model representing an action to be taken on an invoice. This model includes fields for the invoice ID, optional email details (recipient, subject, and body) that can be used to notify relevant parties about the action, and a command that may be executed based on the action. The invoice_id is a required string that identifies the specific invoice associated with the action. The mail_to, mail_subject, and mail_body fields are optional strings that provide details for sending an email notification related to the invoice action, allowing for communication with stakeholders or users about the outcome of the action. The command field is a required string that specifies an action or set of instructions to be executed based on the invoice action, enabling automated processing or handling of the invoice within the system. This model serves as a structured representation of actions that can be performed on invoices, facilitating both communication and automation in response to various events or conditions related to invoices."""

    invoice_id: str
    mail_to: str | None = None
    mail_subject: str | None = None
    mail_body: str | None = None

    model_config = ConfigDict(from_attributes=True)


class InvoiceResponse(BaseModel):
    """Pydantic model representing the response structure for an invoice. This model includes fields for invoice ID, vendor ID, invoice date, due date, currency code, subtotal, tax amount, discount amount, total amount, file URL, timestamps for creation and updates, vendor information (as a VendorBase instance), and a list of invoice items (as InvoiceItemsBase instances). The invoice_id is a string that uniquely identifies the invoice. The vendor_id is an integer that references the associated vendor. The invoice_date and due_date are date fields representing when the invoice was issued and when it is due for payment, respectively. The currency_code is a string that indicates the currency used in the invoice (e.g., "USD", "EUR"). The subtotal, tax_amount, discount_amount (optional), and total_amount are decimal fields that represent the financial details of the invoice. The file_url is a string that provides a link to the file associated with the invoice. The created_at and updated_at fields are datetime fields that automatically record when the invoice record was created and last updated. The vendor field contains detailed information about the vendor associated with the invoice, while the invoice_items field contains a list of items included in the invoice, each with its own description, quantity, unit price, and total price. This model serves as a comprehensive representation of an invoice response that can be returned in API responses or used within the application logic to display or process invoice data."""

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

    model_config = ConfigDict(from_attributes=True)


class DecisionResponse(BaseModel):
    """Pydantic model representing the response structure for a decision made on an invoice. This model includes fields for the invoice ID and the status of the decision (e.g., "approved", "rejected", "review"). The invoice_id is a string that uniquely identifies the invoice associated with the decision. The status field is a string that indicates the outcome of the decision made on the invoice, providing information about whether the invoice was approved, rejected, or marked for review. This model serves as a structured format for returning the results of actions taken on invoices, allowing for easy serialization and validation of the response data when performing operations such as approving, rejecting, or reviewing invoices through the API."""

    invoice_id: str
    status: str

    model_config = ConfigDict(from_attributes=True)
