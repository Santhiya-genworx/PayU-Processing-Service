"""Module: invoice_model.py"""

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import relationship

from src.data.clients.database import Base


class Invoice(Base):
    """SQLAlchemy model representing an invoice. This model defines the structure of the invoices table in the database, including fields for invoice ID, vendor ID, invoice date, due date, currency code, subtotal, tax amount, discount amount, total amount, file URL, and timestamps for creation and updates. It also establishes relationships with the Vendor model (many-to-one) and the InvoiceItem model (one-to-many), allowing for easy access to related data. The invoice_id is the primary key for this table, and the vendor_id is a foreign key referencing the vendors table. The model includes automatic timestamping for when records are created and updated."""

    __tablename__ = "invoices"

    invoice_id = Column(String(255), primary_key=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False)
    invoice_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)
    currency_code = Column(String(3), nullable=False)
    subtotal = Column(Numeric(15, 2), nullable=False)
    tax_amount = Column(Numeric(15, 2), nullable=False)
    discount_amount = Column(Numeric(15, 2), nullable=True)
    total_amount = Column(Numeric(15, 2), nullable=False)
    file_url = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    vendor = relationship("Vendor", back_populates="invoices")
    invoice_items = relationship("InvoiceItem", back_populates="invoice")
    history = relationship("InvoiceUploadHistory", back_populates="invoice")


class InvoiceItem(Base):
    """SQLAlchemy model representing an invoice item. This model defines the structure of the invoice_items table in the database, including fields for item ID, invoice ID, item description, quantity, unit price, total price, and a timestamp for when the record was created. The item_id is the primary key for this table, and the invoice_id is a foreign key referencing the invoices table. The model establishes a relationship with the Invoice model (many-to-one), allowing for easy access to the parent invoice data. This model is used to store individual line items associated with an invoice, including details about the quantity and pricing of each item.  The created_at field automatically records when each invoice item record is created."""

    __tablename__ = "invoice_items"

    item_id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_id = Column(String(255), ForeignKey("invoices.invoice_id"), nullable=False)
    item_description = Column(String(255), nullable=False)
    quantity = Column(Integer, nullable=True)
    unit_price = Column(Numeric(15, 2), nullable=True)
    total_price = Column(Numeric(15, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    invoice = relationship("Invoice", back_populates="invoice_items")
