"""module: matching_schema.py"""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class MatchingStatus(StrEnum):
    """Enumeration representing the status of an invoice matching group. This enum defines the possible states for the matching process, including 'pending' (indicating that the group is awaiting processing), 'approved' (indicating that the matching has been successfully validated), 'rejected' (indicating that the matching has failed validation), and 'reviewed' (indicating that the matching has been reviewed by a human but not yet finalized). This status is used to track the progress of each matching group through the validation workflow and can be updated based on the results of the graph-based validation process or manual review decisions."""

    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    reviewed = "reviewed"


class DecisionStatus(StrEnum):
    """Enumeration representing the decision outcome of an invoice matching group. This enum defines the possible decisions that can be made after validating a matching group, including 'approve' (indicating that the group has been approved for payment), 'reject' (indicating that the group has been rejected and requires further action), and 'review' (indicating that the group requires manual review before a final decision can be made). This decision status is used to capture the outcome of the validation process and can be set based on the results from the validation graph or manual review actions taken by users."""

    approve = "approve"
    reject = "reject"
    review = "review"


class InvoiceMatchingBase(BaseModel):
    """Pydantic model representing the base structure of an invoice matching record. This model includes fields for the unique identifier of the matching record, lists of associated invoice IDs and purchase order IDs, a boolean indicating whether all purchase orders have been matched, the current status of the matching process, the final decision (approve/reject/review), optional command and confidence score from the validation graph, email details for notifications, and timestamps for when the matching record was created and last updated. The model serves as a base for representing the state of an invoice matching group as it goes through the validation and review process, providing a structured format for storing and validating this information within the system."""

    id: int
    invoices: list[str]
    pos: list[str]
    is_po_matched: bool | None
    status: MatchingStatus
    decision: DecisionStatus | None
    command: str | None
    confidence_score: Decimal | None
    mail_to: str | None
    mail_subject: str | None
    mail_body: str | None
    matched_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
