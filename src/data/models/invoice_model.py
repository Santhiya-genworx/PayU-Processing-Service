from sqlalchemy import Column, Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import relationship
from src.data.clients.database import Base
from enum import Enum as PyEnum

class InvoiceStatus(PyEnum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    reviewed = "reviewed"
    paid = "paid"

class Invoice(Base):
    __tablename__ = "invoices"

    invoice_id = Column(String(255), primary_key=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False)
    po_id = Column(String(255),ForeignKey("purchase_orders.po_id"), nullable=False)
    invoice_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)
    currency_code = Column(String(3), nullable=False)
    subtotal = Column(Numeric(15,2), nullable=False)
    tax_amount = Column(Numeric(15,2), nullable=False)
    discount_amount = Column(Numeric(15,2), nullable=True)
    total_amount = Column(Numeric(15,2), nullable=False)
    status = Column(Enum(InvoiceStatus), nullable=False)
    file_url = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    vendor = relationship("Vendor", back_populates="invoices")
    purchase_order = relationship("PurchaseOrder", back_populates="invoice")
    invoice_items =  relationship("InvoiceItem", back_populates="invoice")
    history = relationship("InvoiceUploadHistory", back_populates="invoice")

class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    item_id = Column(Integer, primary_key=True, autoincrement=True)    
    invoice_id = Column(String(255), ForeignKey("invoices.invoice_id"), nullable=False)
    item_description = Column(String(255), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(15,2), nullable=False)
    total_price = Column(Numeric(15,2), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    invoice = relationship("Invoice", back_populates="invoice_items")