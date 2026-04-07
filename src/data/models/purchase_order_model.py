"""module: purchase_order_model.py"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.data.clients.database import Base
from src.data.models.vendor_model import Vendor

if TYPE_CHECKING:
    from src.data.models.upload_history_model import PurchaseOrderUploadHistory


class POStatus(PyEnum):
    """Enumeration representing the status of a purchase order. This enum defines the possible states for a purchase order, including 'pending' (indicating that the purchase order has been created but not yet processed), 'completed' (indicating that the purchase order has been fully processed and fulfilled), and 'cancelled' (indicating that the purchase order has been cancelled and will not be processed). This status is used to track the lifecycle of each purchase order and can be updated based on actions taken by users or automated processes within the system."""

    pending = "pending"
    completed = "completed"
    cancelled = "cancelled"


class PurchaseOrder(Base):
    """SQLAlchemy model representing a purchase order. This model defines the structure of the purchase_orders table in the database, including fields for purchase order ID, vendor ID, GL code, total amount, currency code, ordered date, file URL, status, and timestamps for creation and updates. The po_id is the primary key for this table, and the vendor_id is a foreign key referencing the vendors table. The model establishes relationships with the Vendor model (many-to-one), the OrderedItems model (one-to-many), and the PurchaseOrderUploadHistory model (one-to-many), allowing for easy access to related data. This model is used to store information about purchase orders uploaded into the system, including details about the vendor, financial information, and associated line items. The status field tracks the current state of the purchase order as it goes through processing."""

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
    """SQLAlchemy model representing an ordered item within a purchase order. This model defines the structure of the ordered_items table in the database, including fields for item ID, purchase order ID, item description, quantity, unit price, total price, and a timestamp for when the record was created. The item_id is the primary key for this table, and the po_id is a foreign key referencing the purchase_orders table. The model establishes a relationship with the PurchaseOrder model (many-to-one), allowing for easy access to the parent purchase order data. This model is used to store individual line items associated with a purchase order, including details about the quantity and pricing of each item. The created_at field automatically records when each ordered item record is created."""

    __tablename__ = "ordered_items"

    item_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    po_id: Mapped[str] = mapped_column(ForeignKey("purchase_orders.po_id"), nullable=False)

    item_description: Mapped[str] = mapped_column(String(255))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[float] = mapped_column(Numeric(15, 2))
    total_price: Mapped[float] = mapped_column(Numeric(15, 2))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    purchase_order: Mapped[PurchaseOrder] = relationship(back_populates="ordered_items")
