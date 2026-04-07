"""Module: matching_model.py"""

from datetime import datetime
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import (
    ARRAY,
    Boolean,
    DateTime,
    Enum,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.data.clients.database import Base


class MatchingStatus(PyEnum):
    """Enumeration representing the status of an invoice matching group. This enum defines the possible states for the matching process, including 'pending' (indicating that the group is awaiting processing), 'approved' (indicating that the matching has been successfully validated), 'rejected' (indicating that the matching has failed validation), and 'reviewed' (indicating that the matching has been reviewed by a human but not yet finalized). This status is used to track the progress of each matching group through the validation workflow and can be updated based on the results of the graph-based validation process or manual review decisions."""

    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    reviewed = "reviewed"


class DecisionStatus(PyEnum):
    """Enumeration representing the decision outcome of an invoice matching group. This enum defines the possible decisions that can be made after validating a matching group, including 'approve' (indicating that the group has been approved for payment), 'reject' (indicating that the group has been rejected and requires further action), and 'review' (indicating that the group requires manual review before a final decision can be made). This decision status is used to capture the outcome of the validation process and can be set based on the results from the validation graph or manual review actions taken by users."""

    approve = "approve"
    reject = "reject"
    review = "review"


class InvoiceMatching(Base):
    """SQLAlchemy model representing the matching of invoices and purchase orders. This model defines the structure of the invoice_matching table in the database, which stores information about groups of invoices and their associated purchase orders that are being evaluated for matching. The model includes fields for storing lists of invoice IDs and PO IDs (as PostgreSQL arrays), a boolean indicating whether all POs have been matched, the current status of the matching process, the final decision (approve/reject/review), confidence scores from the validation graph, email details for notifications, and timestamps for when the group was created and last updated. This model is central to tracking the state of each matching group as it goes through the validation and review process."""

    __tablename__ = "invoice_matching"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)

    invoices: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    pos: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)

    is_po_matched: Mapped[bool | None] = mapped_column(Boolean, nullable=True, default=None)

    status: Mapped[MatchingStatus] = mapped_column(
        Enum(MatchingStatus, name="matching_status_enum"), default=MatchingStatus.pending
    )

    decision: Mapped[DecisionStatus | None] = mapped_column(
        Enum(DecisionStatus, name="decision_status_enum"), nullable=True
    )

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
