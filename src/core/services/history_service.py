from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.data.repositories.base_repository import get_data_by_any
from src.data.models.upload_history_model import InvoiceUploadHistory, PurchaseOrderUploadHistory

async def getInvoiceUploadHistory(invoice_id: str, db: AsyncSession):
    try:
        result = await get_data_by_any(InvoiceUploadHistory, db, invoice_id=invoice_id, order_by=InvoiceUploadHistory.action_date.desc())
        return result
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))

async def getPOUploadHistory(po_id: str, db: AsyncSession):
    try:
        result = await get_data_by_any(PurchaseOrderUploadHistory, db, po_id=po_id, order_by=PurchaseOrderUploadHistory.action_date.desc())
        return result
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))