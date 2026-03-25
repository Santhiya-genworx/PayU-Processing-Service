from typing import Annotated, Literal, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, EmailStr

from src.schemas.invoice_schema import InvoiceRequest
from src.schemas.purchase_order_schema import PurchaseOrderRequest


class Decision(BaseModel):
    status: Literal["approve", "review", "reject"]
    confidence_score: float
    command: str
    mail_to: EmailStr | None = None
    mail_subject: str | None = None
    mail_body: str | None = None


class AgentState(TypedDict, total=False):
    invoices: list[InvoiceRequest]
    pos: list[PurchaseOrderRequest]

    messages: Annotated[list[BaseMessage], add_messages]
    output: Decision
