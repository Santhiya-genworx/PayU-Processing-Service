from fastapi import Depends, HTTPException
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.data.models.user_model import Role
from src.core.security.jwt_handler import get_current_user
from src.data.models.vendor_model import Vendor
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
    
async def getRecentActivity(db: AsyncSession, user):
    try:
        invoices = await get_data_by_any(Invoice, db, limit=5, order_by=Invoice.updated_at.desc())
        purchase_orders = await get_data_by_any(PurchaseOrder, db, limit=5, order_by=PurchaseOrder.updated_at.desc())
        
        if user["role"]==Role.admin:
            activity = invoices + purchase_orders 
        else:
            activity = invoices
        activity.sort(key=lambda x: x.updated_at, reverse=True)
        
        top_activity = activity[:5]
        return top_activity

    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))
    
async def filterInvoices(search: str, db: AsyncSession):
    try:
        stmt = select(Invoice).options(selectinload(Invoice.vendor), selectinload(Invoice.invoice_items)).order_by(Invoice.updated_at.desc())
        if search:
            stmt = stmt.where(
                or_(
                    Invoice.invoice_id.ilike(f"{search}%"),
                    Invoice.po_id.ilike(f"{search}%"),
                    cast(Invoice.status, String).ilike(f"{search}%"),
                    Invoice.vendor.has(Vendor.name.ilike(f"{search}%"))
                )
            )

        result = await db.execute(stmt)
        invoices = result.scalars().all()
        return invoices

    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))
    
async def filterPurchaseOrders(search: str, db: AsyncSession):
    try:
        stmt = select(PurchaseOrder).options(selectinload(PurchaseOrder.vendor), selectinload(PurchaseOrder.order_items)).order_by(PurchaseOrder.updated_at.desc())
        if search:
            stmt = stmt.where(
                or_(
                    PurchaseOrder.po_id.ilike(f"{search}%"),
                    PurchaseOrder.gl_code.ilike(f"{search}%"),
                    cast(PurchaseOrder.status, String).ilike(f"%{search}%"),
                    PurchaseOrder.vendor.has(Vendor.name.ilike(f"{search}%"))
                )
            )

        result = await db.execute(stmt)
        purchase_orders = result.scalars().all()

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
