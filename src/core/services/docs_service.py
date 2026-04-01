from datetime import UTC, datetime
from typing import Any

from dateutil.relativedelta import relativedelta
from sqlalchemy import String, cast, extract, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.schemas.purchase_order_schema import PurchaseOrderResponse
from src.schemas.invoice_schema import InvoiceResponse
from src.core.exceptions.exceptions import AppException
from src.data.models.invoice_model import Invoice
from src.data.models.matching_model import InvoiceMatching
from src.data.models.purchase_order_model import PurchaseOrder
from src.data.models.user_model import User
from src.data.models.vendor_model import Vendor
from src.data.repositories.base_repository import get_data_by_any


async def getDocumentCounts(db: AsyncSession) -> dict[str, int]:
    try:
        total_invoices = await db.scalar(select(func.count(Invoice.invoice_id)))
        total_pos = await db.scalar(select(func.count(PurchaseOrder.po_id)))

        status_counts = await db.execute(
            select(
                InvoiceMatching.status,
                func.count(InvoiceMatching.invoice_id),
            ).group_by(InvoiceMatching.status)
        )

        status_map: dict[str, int] = {row[0].value: row[1] for row in status_counts}

        return {
            "total": int((total_invoices or 0) + (total_pos or 0)),
            "approved": status_map.get("approved", 0),
            "pending": status_map.get("pending", 0),
            "reviewed": status_map.get("reviewed", 0),
            "rejected": status_map.get("rejected", 0),
        }

    except Exception as err:
        raise AppException(detail=str(err)) from err


async def getRecentActivity(db: AsyncSession, user: Any) -> list[dict[str, Any]]:
    try:
        query = (
            select(
                InvoiceMatching.invoice_id,
                InvoiceMatching.po_id,
                InvoiceMatching.status,
                InvoiceMatching.is_po_matched,
                Invoice.total_amount,
                Invoice.invoice_date,
                Invoice.updated_at,
            )
            .join(Invoice, Invoice.invoice_id == InvoiceMatching.invoice_id)
            .order_by(InvoiceMatching.updated_at.desc())
            .limit(5)
        )

        rows = await db.execute(query)

        result: list[dict[str, Any]] = []
        for row in rows:
            result.append(
                {
                    "invoice_id": row.invoice_id,
                    "po_id": row.po_id,
                    "status": row.status.value,
                    "is_po_matched": row.is_po_matched,
                    "total_amount": float(row.total_amount or 0),
                    "invoice_date": str(row.invoice_date) if row.invoice_date else None,
                }
            )

        return result

    except Exception as err:
        raise AppException(detail=str(err)) from err


async def filterInvoices(search: str, db: AsyncSession) -> list[InvoiceResponse]:
    try:
        stmt = (
            select(Invoice)
            .options(
                selectinload(Invoice.vendor),
                selectinload(Invoice.invoice_items),
            )
            .order_by(Invoice.updated_at.desc())
        )

        if search:
            stmt = stmt.where(
                or_(
                    Invoice.invoice_id.ilike(f"{search}%"),
                    Invoice.vendor.has(Vendor.name.ilike(f"{search}%")),
                )
            )

        result = await db.execute(stmt)
        return list(result.scalars().all())

    except Exception as err:
        raise AppException(detail=str(err)) from err


async def filterPurchaseOrders(search: str, db: AsyncSession) -> list[PurchaseOrderResponse]:
    try:
        stmt = (
            select(PurchaseOrder)
            .options(
                selectinload(PurchaseOrder.vendor),
                selectinload(PurchaseOrder.ordered_items),
            )
            .order_by(PurchaseOrder.updated_at.desc())
        )

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
        return list(result.scalars().all())

    except Exception as err:
        raise AppException(detail=str(err)) from err


async def getDocumentsStats(db: AsyncSession) -> dict[str, Any]:
    try:
        invoice_docs = await get_data_by_any(Invoice, db)
        po_docs = await get_data_by_any(PurchaseOrder, db)

        invoice_value = await db.scalar(select(func.sum(Invoice.total_amount)))
        po_value = await db.scalar(select(func.sum(PurchaseOrder.total_amount)))

        return {
            "total_invoices": len(invoice_docs),
            "total_pos": len(po_docs),
            "invoice_value": float(invoice_value or 0),
            "po_value": float(po_value or 0),
        }

    except Exception as err:
        raise AppException(detail=str(err)) from err


async def getMonthlyVolume(db: AsyncSession) -> list[dict[str, Any]]:
    try:
        now = datetime.now(UTC)
        months = [now - relativedelta(months=i) for i in range(5, -1, -1)]

        result: list[dict[str, Any]] = []

        for dt in months:
            invoice_count = await db.scalar(
                select(func.count(Invoice.invoice_id)).where(
                    extract("year", Invoice.created_at) == dt.year,
                    extract("month", Invoice.created_at) == dt.month,
                )
            )

            po_count = await db.scalar(
                select(func.count(PurchaseOrder.po_id)).where(
                    extract("year", PurchaseOrder.created_at) == dt.year,
                    extract("month", PurchaseOrder.created_at) == dt.month,
                )
            )

            result.append(
                {
                    "month": dt.strftime("%b"),
                    "invoices": invoice_count or 0,
                    "po": po_count or 0,
                }
            )

        return result

    except Exception as err:
        raise AppException(detail=str(err)) from err


async def getMonthlyAmount(db: AsyncSession) -> list[dict[str, Any]]:
    try:
        now = datetime.now(UTC)
        months = [now - relativedelta(months=i) for i in range(5, -1, -1)]

        result: list[dict[str, Any]] = []

        for dt in months:
            total = await db.scalar(
                select(func.sum(Invoice.total_amount)).where(
                    extract("year", Invoice.created_at) == dt.year,
                    extract("month", Invoice.created_at) == dt.month,
                )
            )

            result.append(
                {
                    "month": dt.strftime("%b"),
                    "amount": float(total or 0),
                }
            )

        return result

    except Exception as err:
        raise AppException(detail=str(err)) from err


async def getQuickStats(db: AsyncSession) -> dict[str, Any]:
    try:
        now = datetime.now(UTC)
        last_month = now - relativedelta(months=1)

        invoices_this_month = await db.scalar(
            select(func.count(Invoice.invoice_id)).where(
                extract("year", Invoice.created_at) == now.year,
                extract("month", Invoice.created_at) == now.month,
            )
        )

        po_this_month = await db.scalar(
            select(func.count(PurchaseOrder.po_id)).where(
                extract("year", PurchaseOrder.created_at) == now.year,
                extract("month", PurchaseOrder.created_at) == now.month,
            )
        )

        active_associates = await db.scalar(
            select(func.count(User.id)).where(User.role == "associate")
        )

        amount_this_month = (
            await db.scalar(
                select(func.sum(Invoice.total_amount)).where(
                    extract("year", Invoice.created_at) == now.year,
                    extract("month", Invoice.created_at) == now.month,
                )
            )
            or 0
        )

        amount_last_month = (
            await db.scalar(
                select(func.sum(Invoice.total_amount)).where(
                    extract("year", Invoice.created_at) == last_month.year,
                    extract("month", Invoice.created_at) == last_month.month,
                )
            )
            or 0
        )

        change_pct: float = (
            round(
                ((float(amount_this_month) - float(amount_last_month)) / float(amount_last_month))
                * 100,
                1,
            )
            if amount_last_month > 0
            else 0.0
        )

        return {
            "invoices_this_month": invoices_this_month or 0,
            "po_this_month": po_this_month or 0,
            "active_associates": active_associates or 0,
            "amount_change_pct": change_pct,
        }

    except Exception as err:
        raise AppException(detail=str(err)) from err


async def getInvoiceMatchings(db: AsyncSession, search: str | None = None) -> list[dict[str, Any]]:
    try:
        stmt = (
            select(InvoiceMatching)
            .join(Invoice, InvoiceMatching.invoice_id == Invoice.invoice_id)
            .options(
                selectinload(InvoiceMatching.invoice).selectinload(Invoice.vendor),
                selectinload(InvoiceMatching.invoice).selectinload(Invoice.invoice_items),
            )
            .order_by(InvoiceMatching.updated_at.desc())
        )

        if search:
            stmt = stmt.where(
                or_(
                    InvoiceMatching.invoice_id.ilike(f"{search}%"),
                    InvoiceMatching.po_id.ilike(f"{search}%"),
                    cast(InvoiceMatching.status, String).ilike(f"{search}%"),
                    cast(InvoiceMatching.decision, String).ilike(f"{search}%"),
                    Invoice.vendor.has(Vendor.name.ilike(f"{search}%")),
                )
            )
        result = await db.execute(stmt)
        matchings = result.scalars().all()

        response = []
        for m in matchings:
            inv = m.invoice
            response.append(
                {
                    "invoice_id": inv.invoice_id,
                    "invoice_date": inv.invoice_date,
                    "total_amount": inv.total_amount,
                    "currency_code": inv.currency_code,
                    "due_date": inv.due_date,
                    "po_id": m.po_id,
                    "matching_status": m.status,
                    "decision": m.decision,
                    "confidence_score": m.confidence_score,
                    "is_po_matched": m.is_po_matched,
                    "command": m.command,
                    "mail_to": m.mail_to,
                    "mail_subject": m.mail_subject,
                    "mail_body": m.mail_body,
                    "vendor": {
                        "name": inv.vendor.name if inv.vendor else None,
                        "email": inv.vendor.email if inv.vendor else None,
                        "mobile_number": inv.vendor.mobile_number if inv.vendor else None,
                        "address": inv.vendor.address if inv.vendor else None,
                    }
                    if inv.vendor
                    else None,
                    "invoice_items": [
                        {
                            "item_description": item.item_description,
                            "quantity": item.quantity,
                            "unit_price": item.unit_price,
                            "total_price": item.total_price,
                        }
                        for item in (inv.invoice_items or [])
                    ],
                    "subtotal": inv.subtotal,
                    "tax_amount": inv.tax_amount
                }
            )
        return response

    except Exception as err:
        raise AppException(detail=str(err)) from err


async def getInvoiceStats(db: AsyncSession) -> dict[str, Any]:
    try:
        total = await db.scalar(select(func.count(Invoice.invoice_id)))

        status_counts = await db.execute(
            select(
                InvoiceMatching.status,
                func.count(InvoiceMatching.invoice_id),
            ).group_by(InvoiceMatching.status)
        )

        status_map: dict[str, int] = {row[0].value: row[1] for row in status_counts}

        total_value = await db.scalar(select(func.sum(Invoice.total_amount))) or 0

        return {
            "total_invoices": int(total or 0),
            "approved": status_map.get("approved", 0),
            "pending": status_map.get("pending", 0),
            "reviewed": status_map.get("reviewed", 0),
            "rejected": status_map.get("rejected", 0),
            "total_value": float(total_value),
        }

    except Exception as err:
        raise AppException(detail=str(err)) from err


async def getPurchaseOrderStats(db: AsyncSession) -> dict[str, Any]:
    try:
        total = await db.scalar(select(func.count(PurchaseOrder.po_id)))

        status_counts = await db.execute(
            select(
                PurchaseOrder.status,
                func.count(PurchaseOrder.po_id),
            ).group_by(PurchaseOrder.status)
        )

        status_map: dict[str, int] = {row[0].value: row[1] for row in status_counts}

        total_value = await db.scalar(select(func.sum(PurchaseOrder.total_amount))) or 0

        return {
            "total_pos": int(total or 0),
            "pending": status_map.get("pending", 0),
            "completed": status_map.get("completed", 0),
            "cancelled": status_map.get("cancelled", 0),
            "total_value": float(total_value),
        }

    except Exception as err:
        raise AppException(detail=str(err)) from err
