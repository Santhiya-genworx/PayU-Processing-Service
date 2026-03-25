from sqlalchemy.ext.asyncio import AsyncSession

from src.schemas.upload_history_schema import InvoiceUploadHistoryBase, PurchaseOrderUploadHistoryBase
from src.core.exceptions.exceptions import AppException
from src.data.models.upload_history_model import (
    InvoiceUploadHistory,
    PurchaseOrderUploadHistory,
)
from src.data.repositories.base_repository import get_data_by_any


async def getInvoiceUploadHistory(invoice_id: str, db: AsyncSession) -> list[InvoiceUploadHistoryBase]:
    try:
        result = await get_data_by_any(
            InvoiceUploadHistory,
            db,
            invoice_id=invoice_id,
            order_by=InvoiceUploadHistory.action_date.desc(),
        )
        return result
    except Exception as err:
        raise AppException(detail=str(err)) from err


async def getPOUploadHistory(po_id: str, db: AsyncSession) -> list[PurchaseOrderUploadHistoryBase]:
    try:
        result = await get_data_by_any(
            PurchaseOrderUploadHistory,
            db,
            po_id=po_id,
            order_by=PurchaseOrderUploadHistory.action_date.desc(),
        )
        return result
    except Exception as err:
        raise AppException(detail=str(err)) from err
