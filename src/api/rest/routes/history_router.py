from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.schemas.upload_history_schema import InvoiceUploadHistoryBase, PurchaseOrderUploadHistoryBase
from src.api.rest.dependencies import get_db
from src.core.services.history_service import (
    getInvoiceUploadHistory,
    getPOUploadHistory,
)

history_router = APIRouter()


@history_router.get("/invoice/history")
async def get_invoice_upload_history(
    invoice_id: str, db: AsyncSession = Depends(get_db)
) -> list[InvoiceUploadHistoryBase]:
    return await getInvoiceUploadHistory(invoice_id, db)


@history_router.get("/purchase-order/history")
async def get_po_upload_history(
    po_id: str, db: AsyncSession = Depends(get_db)
) -> list[PurchaseOrderUploadHistoryBase]:
    return await getPOUploadHistory(po_id, db)
