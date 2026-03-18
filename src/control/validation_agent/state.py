from typing import Literal, TypedDict, Annotated, Optional
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from pydantic import BaseModel, EmailStr
from src.schemas.invoice_schema import InvoiceRequest
from src.schemas.purchase_order_schema import PurchaseOrderRequest

class Decision(BaseModel):
    status: Literal["approve", "review", "reject"]
    confidence_score: float
    command: str
    mail_to: Optional[EmailStr] = None
    mail_subject: Optional[str] = None
    mail_body: Optional[str] = None

class AgentState(TypedDict, total=False):

    invoice: InvoiceRequest
    po: Optional[PurchaseOrderRequest] = None

    messages: Annotated[list[BaseMessage], add_messages]
    output: Decision