from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.schemas.invoice_schema import InvoiceAction
from src.core.services.invoice_service import approveInvoice, rejectInvoice, reviewInvoice
from src.api.rest.dependencies import get_db

invoice_router = APIRouter(prefix="/invoice")

@invoice_router.put("/approve")
async def approve_invoice(data: InvoiceAction, db: AsyncSession = Depends(get_db)):
    return await approveInvoice(data, db)

@invoice_router.put("/review")
async def review_invoice(data: InvoiceAction, db: AsyncSession = Depends(get_db)):
    return await reviewInvoice(data, db)

@invoice_router.put("/reject")
async def reject_invoice(data: InvoiceAction, db: AsyncSession = Depends(get_db)):
    return await rejectInvoice(data, db)