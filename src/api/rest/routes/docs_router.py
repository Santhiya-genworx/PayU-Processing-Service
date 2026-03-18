from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.rest.dependencies import get_db
from src.core.security.jwt_handler import get_current_user
from src.core.services.docs_service import getDocumentCounts, getRecentActivity, filterInvoices, filterPurchaseOrders, getDocumentsStats, getMonthlyVolume, getMonthlyAmount, getQuickStats

docs_router = APIRouter()

@docs_router.get("/document-counts")
async def document_counts(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    return await getDocumentCounts(db)

@docs_router.get("/recent-activity")
async def recent_activity(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    return await getRecentActivity(db, current_user)

@docs_router.get("/documents/invoices/filter")
async def filter_invoices(search: str = "", db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    return await filterInvoices(search, db)

@docs_router.get("/documents/purchase-orders/filter")
async def filter_purchase_orders(search: str = "", db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    return await filterPurchaseOrders(search, db)

@docs_router.get("/documents/stats")
async def documents_stats(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    return await getDocumentsStats(db)

@docs_router.get("/stats/monthly-volume")
async def monthly_volume(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    return await getMonthlyVolume(db)

@docs_router.get("/stats/monthly-amount")
async def monthly_amount(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    return await getMonthlyAmount(db)

@docs_router.get("/stats/quick")
async def quick_stats(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    return await getQuickStats(db)