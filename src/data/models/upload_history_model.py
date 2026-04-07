"""module: upload_history_model.py"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.data.clients.database import Base

if TYPE_CHECKING:
    from src.data.models.invoice_model import Invoice
    from src.data.models.purchase_order_model import PurchaseOrder


class InvoiceUploadHistory(Base):
    """SQLAlchemy model representing the upload history of an invoice. This model defines the structure of the invoice_upload_history table in the database, including fields for history ID, invoice ID, old file URL, new file URL, and the date of the action. The id is the primary key for this table, and the invoice_id is a foreign key referencing the invoices table. The model establishes a relationship with the Invoice model (many-to-one), allowing for easy access to the parent invoice data. This model is used to track changes to invoice uploads, such as when an invoice file is updated or replaced, by storing the previous and new file URLs along with a timestamp of when the change occurred."""

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
    """SQLAlchemy model representing the upload history of a purchase order. This model defines the structure of the purchase_order_upload_history table in the database, including fields for history ID, purchase order ID, old file URL, new file URL, and the date of the action. The id is the primary key for this table, and the po_id is a foreign key referencing the purchase_orders table. The model establishes a relationship with the PurchaseOrder model (many-to-one), allowing for easy access to the parent purchase order data. This model is used to track changes to purchase order uploads, such as when a purchase order file is updated or replaced, by storing the previous and new file URLs along with a timestamp of when the change occurred."""

    __tablename__ = "purchase_order_upload_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    po_id: Mapped[str] = mapped_column(String(255), ForeignKey("purchase_orders.po_id"))
    old_file_url: Mapped[str] = mapped_column(String(255), nullable=False)
    new_file_url: Mapped[str] = mapped_column(String(255), nullable=False)
    action_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    purchase_order: Mapped["PurchaseOrder"] = relationship(
        "PurchaseOrder", back_populates="history"
    )
