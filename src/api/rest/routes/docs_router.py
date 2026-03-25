from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.schemas.invoice_schema import InvoiceResponse
from src.schemas.purchase_order_schema import PurchaseOrderResponse
from src.api.rest.dependencies import get_db
from src.core.security.jwt_handler import get_current_user
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
from src.data.models.invoice_model import Invoice
from src.data.models.purchase_order_model import PurchaseOrder

docs_router = APIRouter()


@docs_router.get("/document-counts")
async def document_counts(
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, int]:
    return await getDocumentCounts(db)


@docs_router.get("/recent-activity")
async def recent_activity(
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    return await getRecentActivity(db, current_user)


@docs_router.get("/documents/invoices/filter")
async def filter_invoices(
    search: str = "",
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> list[InvoiceResponse]:
    return await filterInvoices(search, db)


@docs_router.get("/documents/purchase-orders/filter")
async def filter_purchase_orders(
    search: str = "",
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> list[PurchaseOrderResponse]:
    return await filterPurchaseOrders(search, db)


@docs_router.get("/documents/invoice-matchings")
async def get_invoice_matchings(
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    return await getInvoiceMatchings(db, search)


@docs_router.get("/documents/invoice/stats")
async def get_invoice_stats(
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    return await getInvoiceStats(db)


@docs_router.get("/documents/purchase-order/stats")
async def get_purchase_order_stats(
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    return await getPurchaseOrderStats(db)


@docs_router.get("/stats/monthly-volume")
async def monthly_volume(
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    return await getMonthlyVolume(db)


@docs_router.get("/stats/monthly-amount")
async def monthly_amount(
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    return await getMonthlyAmount(db)


@docs_router.get("/stats/quick")
async def quick_stats(
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    return await getQuickStats(db)
