from __future__ import annotations

from datetime import date, datetime
from enum import Enum as PyEnum

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.data.clients.database import Base
from src.data.models.vendor_model import Vendor
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.data.models.upload_history_model import PurchaseOrderUploadHistory

class POStatus(PyEnum):
    pending = "pending"
    completed = "completed"
    cancelled = "cancelled"


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    po_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id"))

    gl_code: Mapped[str] = mapped_column(String(255))
    total_amount: Mapped[float] = mapped_column(Numeric(15, 2))
    currency_code: Mapped[str] = mapped_column(String(3))
    ordered_date: Mapped[date] = mapped_column(Date)
    file_url: Mapped[str] = mapped_column(String(255))

    status: Mapped[POStatus] = mapped_column(Enum(POStatus, name="po_status_enum"))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    vendor: Mapped[Vendor] = relationship(back_populates="purchase_orders")

    ordered_items: Mapped[list[OrderedItems]] = relationship(
        back_populates="purchase_order", cascade="all, delete-orphan"
    )

    history: Mapped[list[PurchaseOrderUploadHistory]] = relationship(
        back_populates="purchase_order"
    )


class OrderedItems(Base):
    __tablename__ = "ordered_items"

    item_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    po_id: Mapped[str] = mapped_column(ForeignKey("purchase_orders.po_id"), nullable=False)

    item_description: Mapped[str] = mapped_column(String(255))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[float] = mapped_column(Numeric(15, 2))
    total_price: Mapped[float] = mapped_column(Numeric(15, 2))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    purchase_order: Mapped[PurchaseOrder] = relationship(back_populates="ordered_items")
