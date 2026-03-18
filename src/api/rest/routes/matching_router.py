from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.services.matching_service import getInvoiceDecision, validateInvoicePo
from src.api.rest.dependencies import get_db

matching_router = APIRouter()

@matching_router.post("/match/invoice/{invoice_id}")
async def validate_invoice_po(invoice_id: str, db: AsyncSession = Depends(get_db)):
    return await validateInvoicePo(invoice_id, db)

@matching_router.get("/invoice/decision")
async def get_invoice_decision(invoice_id: str, db: AsyncSession = Depends(get_db)):
    return await getInvoiceDecision(invoice_id, db)