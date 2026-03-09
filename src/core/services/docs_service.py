from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.data.models.invoice_model import Invoice
from src.data.models.purchase_order_model import PurchaseOrder
from src.data.repositories.base_repository import get_data_by_any
from sqlalchemy.orm import selectinload

async def getTotalDocuments(db: AsyncSession):
    try:
        invoice_docs = await get_data_by_any(Invoice, db)
        po_docs = await get_data_by_any(PurchaseOrder, db)
        return len(invoice_docs) + len(po_docs)
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))
    
async def getApprovedDocuments(db: AsyncSession):
    try:
        data = {"status": "approved"}
        invoice_docs = await get_data_by_any(Invoice, db, **data)
        return len(invoice_docs)
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))
    
async def getReviewedDocuments(db: AsyncSession):
    try:
        data = {"status": "reviewed"}
        invoice_docs = await get_data_by_any(Invoice, db, **data)
        return len(invoice_docs)
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))
    
async def getRejectedDocuments(db: AsyncSession):
    try:
        data = {"status": "rejected"}
        invoice_docs = await get_data_by_any(Invoice, db, **data)
        return len(invoice_docs)
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))
    
async def getRecentActivity(db: AsyncSession):
    try:
        invoices = await get_data_by_any(Invoice, db, limit=5, order_by=Invoice.updated_at.desc())
        purchase_orders = await get_data_by_any(PurchaseOrder, db, limit=5, order_by=PurchaseOrder.updated_at.desc())

        activity = invoices + purchase_orders
        activity.sort(key=lambda x: x.updated_at, reverse=True)
        top_activity = activity[:5]
        return top_activity

    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))
    
async def getAllInvoices(db: AsyncSession):
    try:
        invoices = await get_data_by_any(
            Invoice,
            db,
            order_by=Invoice.updated_at.desc(),
            options=[selectinload(Invoice.vendor)]
        )

        invoices.sort(key=lambda x: x.updated_at, reverse=True)
        return invoices

    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))
    
async def getAllPurchaseOrders(db: AsyncSession):
    try:
        purchase_orders = await get_data_by_any(
            PurchaseOrder,
            db,
            order_by=PurchaseOrder.updated_at.desc(),
            options=[selectinload(PurchaseOrder.vendor)]
        )

        purchase_orders.sort(key=lambda x: x.updated_at, reverse=True)
        return purchase_orders

    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))
    
async def getDocumentsStats(db: AsyncSession):
    try:
        invoice_docs = await get_data_by_any(Invoice, db)
        po_docs = await get_data_by_any(PurchaseOrder, db)
        total_invoices = len(invoice_docs) 
        total_pos = len(po_docs)
        
        invoice_value = await db.scalar(select(func.sum(Invoice.total_amount)))
        po_value = await db.scalar(select(func.sum(PurchaseOrder.total_amount)))

        return {
            "total_invoices": total_invoices or 0,
            "total_pos": total_pos or 0,
            "invoice_value": invoice_value or 0,
            "po_value": po_value or 0
        }
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))
