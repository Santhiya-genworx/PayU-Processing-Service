from datetime import datetime
from decimal import Decimal
from enum import Enum
from pydantic import BaseModel


class MatchingStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    reviewed = "reviewed"


class DecisionStatus(str, Enum):
    approve = "approve"
    reject = "reject"
    review = "review"


class InvoiceMatchingBase(BaseModel):
    id: int
    invoice_id: str
    po_id: str | None
    is_po_matched: bool
    status: MatchingStatus
    decision: DecisionStatus | None
    command: str | None
    confidence_score: Decimal | None
    mail_to: str | None
    mail_subject: str | None
    mail_body: str | None
    matched_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}