"""module: vendor_model.py"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.data.clients.database import Base

if TYPE_CHECKING:
    from src.data.models.invoice_model import Invoice
    from src.data.models.purchase_order_model import PurchaseOrder


class Vendor(Base):
    """SQLAlchemy model representing a vendor in the system. This model defines the structure of the vendors table in the database, including fields for vendor ID, name, email, address, country code, mobile number, GST number, bank details, and timestamps for creation and updates. The id is the primary key for this table and is set to auto-increment. The email and gst_number fields are unique to ensure that no two vendors can have the same email address or GST number. The model establishes relationships with the Invoice model (one-to-many) and the PurchaseOrder model (one-to-many), allowing for easy access to related data. This model serves as the basis for managing vendor information within the system, including contact details and financial information necessary for processing invoices and purchase orders."""

    __tablename__ = "vendors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    country_code: Mapped[str] = mapped_column(String(3), nullable=False)
    mobile_number: Mapped[str] = mapped_column(String(20), nullable=False)
    gst_number: Mapped[str] = mapped_column(String(15), nullable=False, unique=True)
    bank_name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_holder_name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_number: Mapped[str] = mapped_column(String(50), nullable=False)
    ifsc_code: Mapped[str] = mapped_column(String(20), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    invoices: Mapped[list["Invoice"]] = relationship("Invoice", back_populates="vendor")
    purchase_orders: Mapped[list["PurchaseOrder"]] = relationship(
        "PurchaseOrder", back_populates="vendor"
    )
