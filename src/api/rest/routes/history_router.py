from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.services.history_service import getInvoiceUploadHistory, getPOUploadHistory
from src.api.rest.dependencies import get_db

history_router = APIRouter()

@history_router.get("/invoice/history")
async def get_invoice_upload_history(invoice_id: str, db: AsyncSession = Depends(get_db)):
    return await getInvoiceUploadHistory(invoice_id, db)

@history_router.get("/purchase-order/history")
async def get_po_upload_history(po_id: str, db: AsyncSession = Depends(get_db)):
    return await getPOUploadHistory(po_id, db)