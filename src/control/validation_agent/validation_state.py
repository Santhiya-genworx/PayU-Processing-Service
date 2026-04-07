"""Module defining the AgentState TypedDict and Decision model for the validation agent graph. This module provides structured definitions for the state used by the agents in the validation graph, including fields for lists of invoices and purchase orders, messages for communication between agents, and the final decision output. The Decision model defines the structure of the output from the validation process, including the status of the validation, confidence score, command for further processing, and optional fields for email communication. The AgentState TypedDict allows for optional fields (total=False) to accommodate different stages of the graph execution where certain pieces of information may not yet be available. This structured state is essential for maintaining consistency and clarity in the data being processed by the various agents in the graph, enabling effective validation of invoices against purchase orders and facilitating communication of results through messages and decisions."""

from typing import Annotated, Literal, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, EmailStr

from src.schemas.invoice_schema import InvoiceRequest
from src.schemas.purchase_order_schema import PurchaseOrderRequest


class Decision(BaseModel):
    """Model defining the structure of the decision output from the validation graph. This model includes fields for the status of the validation (approve, review, reject), a confidence score indicating the certainty of the decision, a command that may be used for further processing or actions, and optional fields for email communication (mail_to, mail_subject, mail_body) that can be utilized if the decision requires sending an email notification. The Decision model provides a clear and structured format for representing the results of the validation process, facilitating downstream handling of the validation outcomes."""

    status: Literal["approve", "review", "reject"]
    confidence_score: float
    command: str
    mail_to: EmailStr | None = None
    mail_subject: str | None = None
    mail_body: str | None = None


class AgentState(TypedDict, total=False):
    """TypedDict defining the structure of the agent state used in the validation graph. This state includes fields for lists of invoices and purchase orders, as well as messages for communication between agents and the final decision output. The fields are optional (total=False) to allow for flexibility in the state during different stages of the graph execution. This structured state is essential for maintaining consistency and clarity in the data being processed by the various agents in the graph, enabling effective validation of invoices against purchase orders and facilitating communication of results through messages and decisions."""

    invoices: list[InvoiceRequest]
    pos: list[PurchaseOrderRequest]

    messages: Annotated[list[BaseMessage], add_messages]
    output: Decision
