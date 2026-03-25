from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.schemas.matching_schema import InvoiceMatchingBase
from src.api.rest.dependencies import get_db
from src.control.validation_agent.validation_graph import invoke_graph
from src.core.services.matching_service import getInvoiceDecision, validateInvoicePo
from src.schemas.graph_output_schema import GraphResult
from src.schemas.invoice_schema import InvoiceRequest
from src.schemas.purchase_order_schema import PurchaseOrderRequest

matching_router = APIRouter()


@matching_router.post("/match/invoice/{invoice_id}")
async def validate_invoice_po(invoice_id: str, type: str) -> GraphResult:
    return await validateInvoicePo(invoice_id, type)


@matching_router.get("/invoice/decision")
async def get_invoice_decision(
    invoice_id: str, db: AsyncSession = Depends(get_db)
) -> list[InvoiceMatchingBase]:
    return await getInvoiceDecision(invoice_id, db)


@matching_router.post("/match")
async def get_match_info(
    invoices: list[InvoiceRequest], pos: list[PurchaseOrderRequest]
) -> GraphResult:
    return await invoke_graph(invoices, pos)
