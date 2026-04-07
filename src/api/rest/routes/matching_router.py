"""This module defines the API routes for handling matching-related actions such as validating matching groups, retrieving invoice matching decisions, and directly invoking the LLM graph with explicit invoice and purchase order payloads. The routes are organized under the "/match" prefix and utilize FastAPI's APIRouter for modularity. Each route interacts with the database using SQLAlchemy's AsyncSession to execute the corresponding service functions that handle the business logic for each action. The responses from these routes are structured according to the defined Pydantic schemas, providing relevant information about the outcomes of the matching operations performed on invoices and purchase orders."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.rest.dependencies import get_db
from src.control.validation_agent.validation_graph import invoke_graph
from src.core.services.matching_service import getInvoiceDecision, validateInvoicePo
from src.schemas.graph_output_schema import GraphResult
from src.schemas.invoice_schema import InvoiceRequest
from src.schemas.matching_schema import InvoiceMatchingBase
from src.schemas.purchase_order_schema import PurchaseOrderRequest

matching_router = APIRouter()


@matching_router.post("/match/group/{group_id}")
async def validate_group(group_id: int, type: str) -> GraphResult:
    """Manually trigger LLM validation for a matching group by its group_id."""
    return await validateInvoicePo(group_id, type)


@matching_router.get("/invoice/decision")
async def get_invoice_decision(
    invoice_id: str, db: AsyncSession = Depends(get_db)
) -> list[InvoiceMatchingBase]:
    """Get the matching group decision for a given invoice_id."""
    return await getInvoiceDecision(invoice_id, db)


@matching_router.post("/match")
async def get_match_info(
    invoices: list[InvoiceRequest], pos: list[PurchaseOrderRequest]
) -> GraphResult:
    """Directly invoke the LLM graph with explicit invoice and PO payloads."""
    return await invoke_graph(invoices, pos)
