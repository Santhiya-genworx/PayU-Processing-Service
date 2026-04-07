"""API router for the PayU Processing Service."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.rest.dependencies import get_db
from src.core.services.docs_service import (
    filterInvoices,
    filterPurchaseOrders,
    getDocumentCounts,
    getInvoiceMatchings,
    getInvoiceStats,
    getMonthlyAmount,
    getMonthlyVolume,
    getPurchaseOrderStats,
    getQuickStats,
    getRecentActivity,
)
from src.schemas.docs_schema import (
    DocumentCountsResponse,
    InvoiceMatchingResponse,
    InvoiceStatsResponse,
    MonthlyAmountItem,
    MonthlyVolumeItem,
    PurchaseOrderStatsResponse,
    QuickStatsResponse,
    RecentActivityItem,
)
from src.schemas.invoice_schema import InvoiceResponse
from src.schemas.purchase_order_schema import PurchaseOrderResponse

docs_router = APIRouter()


@docs_router.get("/document-counts")
async def document_counts(db: AsyncSession = Depends(get_db)) -> DocumentCountsResponse:
    """Endpoint to retrieve counts of various document types.
    This endpoint returns the total counts of invoices, purchase orders, and matched documents in the system. It requires authentication and uses the database session to query the relevant data. The response is a JSON object containing the counts for each document type.
    Args:
    db (AsyncSession): The database session dependency for querying the database.
    Returns:                A dictionary containing the counts of invoices, purchase orders, and matched documents.
    """
    return await getDocumentCounts(db)


@docs_router.get("/recent-activity")
async def recent_activity(db: AsyncSession = Depends(get_db)) -> list[RecentActivityItem]:
    """Endpoint to retrieve recent activity on documents.
    This endpoint returns a list of the 5 most recently updated matching groups, including the total amount across all invoices in each group. It uses the database session to query the relevant data and does not require authentication, allowing it to be accessed by any user. The response is a list of dictionaries, each representing a matching group with its recent activity details.
    Args:
    db (AsyncSession): The database session dependency for querying the database.
    Returns:                A list of dictionaries, each containing details of recent activity on matching groups.
    """
    return await getRecentActivity(db)


@docs_router.get("/documents/invoices/filter")
async def filter_invoices(
    search: str = "",
    db: AsyncSession = Depends(get_db),
) -> list[InvoiceResponse]:
    """Endpoint to filter invoices based on a search query.
    Args:
    search (str): The search query to filter invoices.
    db (AsyncSession): The database session dependency for querying the database.
    Returns:                A list of filtered invoice responses.
    """

    return await filterInvoices(search, db)


@docs_router.get("/documents/purchase-orders/filter")
async def filter_purchase_orders(
    search: str = "", db: AsyncSession = Depends(get_db)
) -> list[PurchaseOrderResponse]:
    """Endpoint to filter purchase orders based on a search query.
    Args:
    search (str): The search query to filter purchase orders.
    db (AsyncSession): The database session dependency for querying the database.
    Returns:                A list of filtered purchase order responses.
    """
    return await filterPurchaseOrders(search, db)


@docs_router.get("/documents/invoice-matchings")
async def get_invoice_matchings(
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[InvoiceMatchingResponse]:
    """Endpoint to retrieve invoice matchings based on a search query.
    Args:
    search (str | None): The search query to filter invoice matchings.
    db (AsyncSession): The database session dependency for querying the database.
    Returns:                A list of dictionaries, each containing details of invoice matchings.
    """

    return await getInvoiceMatchings(db, search)


@docs_router.get("/documents/invoice/stats")
async def get_invoice_stats(db: AsyncSession = Depends(get_db)) -> InvoiceStatsResponse:
    """Endpoint to retrieve statistics about invoices."""
    return await getInvoiceStats(db)


@docs_router.get("/documents/purchase-order/stats")
async def get_purchase_order_stats(
    db: AsyncSession = Depends(get_db),
) -> PurchaseOrderStatsResponse:
    """Endpoint to retrieve statistics about purchase orders."""
    return await getPurchaseOrderStats(db)


@docs_router.get("/stats/monthly-volume")
async def monthly_volume(db: AsyncSession = Depends(get_db)) -> list[MonthlyVolumeItem]:
    """Endpoint to retrieve monthly volume statistics.
    This endpoint returns a list of dictionaries, each containing the total volume of documents processed for each month. It uses the database session to query the relevant data and does not require authentication, allowing it to be accessed by any user. The response is a list of dictionaries, each representing a month with its corresponding document volume.
    Args:    db (AsyncSession): The database session dependency for querying the database.
    Returns:                A list of dictionaries, each containing the total volume of documents processed for each month.
    """
    return await getMonthlyVolume(db)


@docs_router.get("/stats/monthly-amount")
async def monthly_amount(
    db: AsyncSession = Depends(get_db),
) -> list[MonthlyAmountItem]:
    """Endpoint to retrieve monthly amount statistics.
    This endpoint returns a list of dictionaries, each containing the total amount of documents processed for each month. It uses the database session to query the relevant data and does not require authentication, allowing it to be accessed by any user. The response is a list of dictionaries, each representing a month with its corresponding document amount.
    Args:    db (AsyncSession): The database session dependency for querying the database.
    Returns:                A list of dictionaries, each containing the total amount of documents processed for each month.
    """
    return await getMonthlyAmount(db)


@docs_router.get("/stats/quick")
async def quick_stats(db: AsyncSession = Depends(get_db)) -> QuickStatsResponse:
    """Endpoint to retrieve quick statistics about documents.
    This endpoint returns a dictionary containing quick statistics about the documents in the system, such as total counts, recent activity, and other relevant metrics. It uses the database session to query the necessary data and does not require authentication, allowing it to be accessed by any user. The response is a dictionary containing various quick statistics about the documents in the system.
    Args:    db (AsyncSession): The database session dependency for querying the database.
    Returns:                A dictionary containing various quick statistics about the documents in the system.
    """
    return await getQuickStats(db)
