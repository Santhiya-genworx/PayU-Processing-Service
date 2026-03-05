from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, Numeric, String, func, Enum
from sqlalchemy.orm import relationship
from src.data.clients.database import Base
from enum import Enum as PyEnum

class POStatus(PyEnum):
    pending = "pending"
    completed = "completed"
    cancelled = "cancelled"

class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    po_id = Column(String(255), primary_key=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False)
    gl_code = Column(String(255), nullable=False)
    total_amount = Column(Numeric(15,2), nullable=False)
    currency_code = Column(String(3), nullable=False)
    ordered_date = Column(Date, nullable=False)
    file_url = Column(String(255), nullable=False)
    status = Column(Enum(POStatus), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    vendor = relationship("Vendor", back_populates="purchase_orders")
    order_items = relationship("OrderedItems", back_populates="purchase_order")
    invoice = relationship("Invoice", back_populates="purchase_order")
    history = relationship("PurchaseOrderUploadHistory", back_populates="purchase_order")

class OrderedItems(Base):
    __tablename__ = "ordered_items"

    item_id = Column(Integer, primary_key=True, autoincrement=True)
    po_id = Column(String(255), ForeignKey("purchase_orders.po_id"), nullable=False)
    item_description = Column(String(255), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(15,2), nullable=False)
    total_price = Column(Numeric(15,2), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    purchase_order = relationship("PurchaseOrder", back_populates="order_items")