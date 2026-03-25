from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.data.clients.database import Base

if TYPE_CHECKING:
    from src.data.models.invoice_model import Invoice
    from src.data.models.purchase_order_model import PurchaseOrder


class InvoiceUploadHistory(Base):
    __tablename__ = "invoice_upload_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    invoice_id: Mapped[str] = mapped_column(String(255), ForeignKey("invoices.invoice_id"))
    old_file_url: Mapped[str] = mapped_column(String(255), nullable=False)
    new_file_url: Mapped[str] = mapped_column(String(255), nullable=False)
    action_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    invoice: Mapped["Invoice"] = relationship("Invoice", back_populates="history")


class PurchaseOrderUploadHistory(Base):
    __tablename__ = "purchase_order_upload_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    po_id: Mapped[str] = mapped_column(String(255), ForeignKey("purchase_orders.po_id"))
    old_file_url: Mapped[str] = mapped_column(String(255), nullable=False)
    new_file_url: Mapped[str] = mapped_column(String(255), nullable=False)
    action_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    purchase_order: Mapped["PurchaseOrder"] = relationship("PurchaseOrder", back_populates="history")