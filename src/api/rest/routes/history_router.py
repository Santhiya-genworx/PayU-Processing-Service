"""This module defines the API routes for retrieving the upload history of invoices and purchase orders. It includes endpoints for fetching the upload history based on invoice ID and purchase order ID. The routes are organized under the "/history" prefix and utilize FastAPI's APIRouter for modularity. The module interacts with a database using SQLAlchemy's AsyncSession to retrieve the relevant history data, which is then returned in a structured format defined by Pydantic schemas."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.rest.dependencies import get_db
from src.core.services.history_service import (
    getInvoiceUploadHistory,
    getPOUploadHistory,
)
from src.schemas.upload_history_schema import (
    InvoiceUploadHistoryBase,
    PurchaseOrderUploadHistoryBase,
)

history_router = APIRouter()


@history_router.get("/invoice/history")
async def get_invoice_upload_history(
    invoice_id: str, db: AsyncSession = Depends(get_db)
) -> list[InvoiceUploadHistoryBase]:
    """API route to retrieve the upload history of an invoice based on its ID. This endpoint accepts an invoice ID as a query parameter and uses the database session to query the relevant upload history data for that invoice. The retrieved history data is returned as a list of structured objects defined by the InvoiceUploadHistoryBase schema. This allows clients to view the upload history of a specific invoice, including details such as upload timestamps, file names, and any associated metadata. Args:   invoice_id (str): The unique identifier for the invoice whose upload history is being retrieved. db (AsyncSession): The database session dependency for querying the database. Returns:    A list of InvoiceUploadHistoryBase objects containing the upload history details for the specified invoice."""
    return await getInvoiceUploadHistory(invoice_id, db)


@history_router.get("/purchase-order/history")
async def get_po_upload_history(
    po_id: str, db: AsyncSession = Depends(get_db)
) -> list[PurchaseOrderUploadHistoryBase]:
    """API route to retrieve the upload history of a purchase order based on its ID. This endpoint accepts a purchase order ID as a query parameter and uses the database session to query the relevant upload history data for that purchase order. The retrieved history data is returned as a list of structured objects defined by the PurchaseOrderUploadHistoryBase schema. This allows clients to view the upload history of a specific purchase order, including details such as upload timestamps, file names, and any associated metadata. Args:   po_id (str): The unique identifier for the purchase order whose upload history is being retrieved. db (AsyncSession): The database session dependency for querying the database. Returns:    A list of PurchaseOrderUploadHistoryBase objects containing the upload history details for the specified purchase order."""
    return await getPOUploadHistory(po_id, db)
