from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.rest.dependencies import get_db
from src.core.services.docs_service import getAllInvoices, getAllPurchaseOrders, getApprovedDocuments, getDocumentsStats, getRecentActivity, getRejectedDocuments, getReviewedDocuments, getTotalDocuments

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

@docs_router.get("/view-documents/invoices")
async def get_all_invoices(db: AsyncSession = Depends(get_db)):
    return await getAllInvoices(db)

@docs_router.get("/view-documents/purchase-orders")
async def get_all_purchase_orders(db: AsyncSession = Depends(get_db)):
    return await getAllPurchaseOrders(db)

@docs_router.get("/documents/stats")
async def get_documents_stats(db: AsyncSession = Depends(get_db)):
    return await getDocumentsStats(db)