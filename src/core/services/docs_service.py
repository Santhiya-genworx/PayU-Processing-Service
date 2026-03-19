from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
from fastapi import HTTPException
from sqlalchemy import String, cast, extract, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from src.data.models.invoice_model import Invoice
from src.data.models.purchase_order_model import PurchaseOrder
from src.data.models.user_model import Role, User
from src.data.models.vendor_model import Vendor
from src.data.repositories.base_repository import get_data_by_any

async def getDocumentCounts(db: AsyncSession):
    try:
        invoice_docs = await get_data_by_any(Invoice, db)
        po_docs      = await get_data_by_any(PurchaseOrder, db)

        approved_docs = await get_data_by_any(Invoice, db, status="approved")
        pending_docs = await get_data_by_any(Invoice, db, status="pending")
        reviewed_docs = await get_data_by_any(Invoice, db, status="reviewed")
        rejected_docs = await get_data_by_any(Invoice, db, status="rejected")

        return {
            "total": len(invoice_docs) + len(po_docs),
            "approved": len(approved_docs),
            "pending" : len(pending_docs),
            "reviewed": len(reviewed_docs),
            "rejected": len(rejected_docs),
        }

    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))

async def getRecentActivity(db: AsyncSession, user):
    try:
        invoices = await get_data_by_any(Invoice, db, limit=5, order_by=Invoice.updated_at.desc())
        purchase_orders = await get_data_by_any(PurchaseOrder, db, limit=5, order_by=PurchaseOrder.updated_at.desc())

        activity = invoices + purchase_orders if user["role"] == Role.admin else invoices
        activity.sort(key=lambda x: x.updated_at, reverse=True)

        return activity[:5]

    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))
    
async def filterInvoices(search: str, db: AsyncSession):
    try:
        stmt = (select(Invoice).options(selectinload(Invoice.vendor), selectinload(Invoice.invoice_items)).order_by(Invoice.updated_at.desc()))
        if search:
            stmt = stmt.where(
                or_(
                    Invoice.invoice_id.ilike(f"{search}%"),
                    Invoice.po_id.ilike(f"{search}%"),
                    cast(Invoice.status, String).ilike(f"{search}%"),
                    Invoice.vendor.has(Vendor.name.ilike(f"{search}%")),
                )
            )

        result = await db.execute(stmt)
        invoices = result.scalars().all()
        return invoices

    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))

async def filterPurchaseOrders(search: str, db: AsyncSession):
    try:
        stmt = (select(PurchaseOrder).options(selectinload(PurchaseOrder.vendor), selectinload(PurchaseOrder.ordered_items)).order_by(PurchaseOrder.updated_at.desc()))
        if search:
            stmt = stmt.where(
                or_(
                    PurchaseOrder.po_id.ilike(f"{search}%"),
                    PurchaseOrder.gl_code.ilike(f"{search}%"),
                    cast(PurchaseOrder.status, String).ilike(f"%{search}%"),
                    PurchaseOrder.vendor.has(Vendor.name.ilike(f"{search}%")),
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
        po_docs      = await get_data_by_any(PurchaseOrder, db)

        invoice_value = await db.scalar(select(func.sum(Invoice.total_amount)))
        po_value      = await db.scalar(select(func.sum(PurchaseOrder.total_amount)))

        return {
            "total_invoices": len(invoice_docs),
            "total_pos":      len(po_docs),
            "invoice_value":  float(invoice_value or 0),
            "po_value":       float(po_value or 0),
        }

    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))

async def getMonthlyVolume(db: AsyncSession):
    try:
        now    = datetime.now(timezone.utc)
        months = [now - relativedelta(months=i) for i in range(5, -1, -1)]

        result = []
        for dt in months:
            invoice_count = await db.scalar(select(func.count(Invoice.invoice_id)).where(extract("year", Invoice.created_at) == dt.year, extract("month", Invoice.created_at) == dt.month))
            po_count = await db.scalar(select(func.count(PurchaseOrder.po_id)).where(extract("year",  PurchaseOrder.created_at) == dt.year, extract("month", PurchaseOrder.created_at) == dt.month))
            result.append({
                "month":    dt.strftime("%b"),
                "invoices": invoice_count or 0,
                "po":       po_count or 0,
            })

        return result

    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))

async def getMonthlyAmount(db: AsyncSession):
    try:
        now    = datetime.now(timezone.utc)
        months = [now - relativedelta(months=i) for i in range(5, -1, -1)]

        result = []
        for dt in months:
            total = await db.scalar(
                select(func.sum(Invoice.total_amount)).where(extract("year",  Invoice.created_at) == dt.year, extract("month", Invoice.created_at) == dt.month,))
            result.append({
                "month":  dt.strftime("%b"),
                "amount": float(total or 0),
            })

        return result

    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))

async def getQuickStats(db: AsyncSession):
    try:
        now        = datetime.now(timezone.utc)
        last_month = now - relativedelta(months=1)

        invoices_this_month = await db.scalar(select(func.count(Invoice.invoice_id)).where(extract("year",  Invoice.created_at) == now.year, extract("month", Invoice.created_at) == now.month,))
        po_this_month = await db.scalar(select(func.count(PurchaseOrder.po_id)).where(extract("year",  PurchaseOrder.created_at) == now.year, extract("month", PurchaseOrder.created_at) == now.month,))

        active_associates = await db.scalar(select(func.count(User.id)).where(User.role == Role.associate))

        amount_this_month = await db.scalar(select(func.sum(Invoice.total_amount)).where(extract("year",  Invoice.created_at) == now.year, extract("month", Invoice.created_at) == now.month,)) or 0
        amount_last_month = await db.scalar(select(func.sum(Invoice.total_amount)).where(extract("year",  Invoice.created_at) == last_month.year, extract("month", Invoice.created_at) == last_month.month,)) or 0

        if amount_last_month > 0:
            change_pct = round(((float(amount_this_month) - float(amount_last_month)) / float(amount_last_month)) * 100, 1,)
        else:
            change_pct = 0.0

        return {
            "invoices_this_month": invoices_this_month or 0,
            "po_this_month":       po_this_month or 0,
            "active_associates":   active_associates or 0,
            "amount_change_pct":   change_pct,
        }

    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))