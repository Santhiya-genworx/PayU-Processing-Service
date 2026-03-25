from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum as PyEnum

from src.data.models.invoice_model import Invoice
from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.data.clients.database import Base


class MatchingStatus(PyEnum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    reviewed = "reviewed"


class DecisionStatus(PyEnum):
    approve = "approve"
    reject = "reject"
    review = "review"


class InvoiceMatching(Base):
    __tablename__ = "invoice_matching"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    invoice_id: Mapped[str] = mapped_column(ForeignKey("invoices.invoice_id"), nullable=False)

    po_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    is_po_matched: Mapped[bool] = mapped_column(Boolean, default=False)

    status: Mapped[MatchingStatus] = mapped_column(
        Enum(MatchingStatus, name="matching_status_enum"), default=MatchingStatus.pending
    )

    decision: Mapped[DecisionStatus | None] = mapped_column(Enum(DecisionStatus, name="decision_status_enum"), nullable=True)

    command: Mapped[str | None] = mapped_column(String(255), nullable=True)

    confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)

    mail_to: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mail_subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mail_body: Mapped[str | None] = mapped_column(Text, nullable=True)

    matched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (UniqueConstraint("invoice_id", "po_id", name="uq_invoice_po_matching"),)

    invoice: Mapped[Invoice] = relationship(back_populates="invoice_matching")
