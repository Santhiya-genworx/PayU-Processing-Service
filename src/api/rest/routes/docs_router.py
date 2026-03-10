from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.rest.dependencies import get_db
from src.core.services.docs_service import filterInvoices, filterPurchaseOrders, getApprovedDocuments, getDocumentsStats, getRecentActivity, getRejectedDocuments, getReviewedDocuments, getTotalDocuments

docs_router = APIRouter()

@docs_router.get("/total-documents")
async def get_total_documents(db: AsyncSession = Depends(get_db)):
    return await getTotalDocuments(db)

@docs_router.get("/approved-documents")
async def get_approved_documents(db: AsyncSession = Depends(get_db)):
    return await getApprovedDocuments(db)

@docs_router.get("/reviewed-documents")
async def get_reviewed_documents(db: AsyncSession = Depends(get_db)):
    return await getReviewedDocuments(db)

@docs_router.get("/rejected-documents")
async def get_rejected_documents(db: AsyncSession = Depends(get_db)):
    return await getRejectedDocuments(db)

@docs_router.get("/recent-activity")
async def get_recent_activity(db: AsyncSession = Depends(get_db)):
    return await getRecentActivity(db)

@docs_router.get("/documents/invoices/filter")
async def get_all_invoices(search: str | None = None,db: AsyncSession = Depends(get_db)):
    return await filterInvoices(search, db)

@docs_router.get("/documents/purchase-orders/filter")
async def get_all_purchase_orders(search: str | None = None,db: AsyncSession = Depends(get_db)):
    return await filterPurchaseOrders(search, db)

@docs_router.get("/documents/stats")
async def get_documents_stats(db: AsyncSession = Depends(get_db)):
    return await getDocumentsStats(db)