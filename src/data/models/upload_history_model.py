from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship
from src.data.clients.database import Base

class InvoiceUploadHistory(Base):
    __tablename__ = "invoice_upload_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_id = Column(String(255), ForeignKey("invoices.invoice_id"))
    old_file_url = Column(String(255), nullable=False)
    new_file_url = Column(String(255), nullable=False)
    action_date = Column(DateTime(timezone=True), server_default=func.now())

    invoice = relationship("Invoice", back_populates="history")

class PurchaseOrderUploadHistory(Base):
    __tablename__ = "purchase_order_upload_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    po_id = Column(String(255), ForeignKey("purchase_orders.po_id"))
    old_file_url = Column(String(255), nullable=False)
    new_file_url = Column(String(255), nullable=False)
    action_date = Column(DateTime(timezone=True), server_default=func.now())

    purchase_order = relationship("PurchaseOrder", back_populates="history")