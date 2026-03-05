from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.data.models.invoice_model import Invoice
from src.data.models.purchase_order_model import PurchaseOrder
from src.data.repositories.base_repository import get_data_by_any

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