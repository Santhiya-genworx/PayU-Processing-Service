"""Module: history_service.py"""

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions.exceptions import AppException
from src.data.models.upload_history_model import (
    InvoiceUploadHistory,
    PurchaseOrderUploadHistory,
)
from src.data.repositories.base_repository import get_data_by_any
from src.schemas.upload_history_schema import (
    InvoiceUploadHistoryBase,
    PurchaseOrderUploadHistoryBase,
)


async def getInvoiceUploadHistory(
    invoice_id: str, db: AsyncSession
) -> list[InvoiceUploadHistoryBase]:
    """Function to retrieve the upload history of a specific invoice. This function queries the database for all upload history records associated with the given invoice ID, ordered by the action date in descending order. It uses SQLAlchemy's AsyncSession to execute the query and returns a list of InvoiceUploadHistoryBase objects representing the upload history of the specified invoice. If any errors occur during the database operations, an AppException is raised with details about the error."""
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
    """Function to retrieve the upload history of a specific purchase order. This function queries the database for all upload history records associated with the given purchase order ID, ordered by the action date in descending order. It uses SQLAlchemy's AsyncSession to execute the query and returns a list of PurchaseOrderUploadHistoryBase objects representing the upload history of the specified purchase order. If any errors occur during the database operations, an AppException is raised with details about the error."""
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
