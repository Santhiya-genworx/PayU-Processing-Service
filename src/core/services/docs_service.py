"""Module for document-related services in the PayU Processing Service application. This module provides functions to retrieve counts of documents, recent activity, filter invoices and purchase orders, and gather various statistics related to invoices and purchase orders. The functions interact with the database using SQLAlchemy's AsyncSession to perform queries and return structured data that can be used by the application's API endpoints or other services. Each function is designed to handle exceptions gracefully, raising an AppException with a detailed error message if any issues occur during database operations."""

from datetime import UTC, datetime

from dateutil.relativedelta import relativedelta
from sqlalchemy import String, cast, extract, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.exceptions.exceptions import AppException
from src.data.models.invoice_model import Invoice
from src.data.models.matching_model import InvoiceMatching
from src.data.models.purchase_order_model import PurchaseOrder
from src.data.models.user_model import User
from src.data.models.vendor_model import Vendor
from src.data.repositories.base_repository import get_data_by_any
from src.schemas.docs_schema import (
    DocumentCountsResponse,
    InvoiceMatchingInvoice,
    InvoiceMatchingPO,
    InvoiceMatchingResponse,
    InvoiceStatsResponse,
    MonthlyAmountItem,
    MonthlyVolumeItem,
    PurchaseOrderStatsResponse,
    QuickStatsResponse,
    RecentActivityItem,
    VendorResponse,
)
from src.schemas.invoice_schema import InvoiceResponse
from src.schemas.purchase_order_schema import PurchaseOrderResponse


async def getDocumentCounts(db: AsyncSession) -> DocumentCountsResponse:
    """Function to retrieve counts of various document types. This function queries the database to count the total number of invoices, purchase orders, and matched documents in the system. It uses SQLAlchemy's AsyncSession to execute the necessary queries and returns a dictionary containing the counts for each document type. The function also includes error handling to manage any exceptions that may arise during the database operations, ensuring that meaningful error messages are provided when issues occur."""
    try:
        total_invoices = await db.scalar(select(func.count(Invoice.invoice_id)))
        total_pos = await db.scalar(select(func.count(PurchaseOrder.po_id)))

        # Count groups by status
        status_counts = await db.execute(
            select(
                InvoiceMatching.status,
                func.count(InvoiceMatching.id),
            ).group_by(InvoiceMatching.status)
        )
        status_map: dict[str, int] = {row[0].value: row[1] for row in status_counts}

        return DocumentCountsResponse(
            total=sum(status_map.values()),
            approved=status_map.get("approved", 0),
            pending=status_map.get("pending", 0),
            reviewed=status_map.get("reviewed", 0),
            rejected=status_map.get("rejected", 0),
            total_invoices=int(total_invoices or 0),
            total_pos=int(total_pos or 0),
        )

    except Exception as err:
        raise AppException(detail=str(err)) from err


async def getRecentActivity(db: AsyncSession) -> list[RecentActivityItem]:
    """Function to retrieve recent activity on documents. This function queries the database to fetch the 5 most recently updated matching groups, including the total amount across all invoices in each group. It uses SQLAlchemy's AsyncSession to execute the necessary queries and returns a list of dictionaries, each representing a matching group with its recent activity details. The function also includes error handling to manage any exceptions that may arise during the database operations, ensuring that meaningful error messages are provided when issues occur."""
    try:
        stmt = select(InvoiceMatching).order_by(InvoiceMatching.updated_at.desc()).limit(5)
        result = await db.execute(stmt)
        groups = result.scalars().all()

        activity: list[RecentActivityItem] = []

        for group in groups:
            accumulated_amount: float = 0.0
            latest_invoice_date: str | None = None

            for invoice_id in group.invoices:
                records = await get_data_by_any(Invoice, db, invoice_id=invoice_id)
                if not records:
                    continue
                inv = records[0]
                accumulated_amount += float(inv.total_amount or 0)
                if inv.invoice_date is not None:
                    date_str = str(inv.invoice_date)
                    if latest_invoice_date is None or date_str > latest_invoice_date:
                        latest_invoice_date = date_str

            activity.append(
                RecentActivityItem(
                    group_id=group.id,
                    invoices=group.invoices,
                    pos=group.pos,
                    status=group.status.value,
                    is_po_matched=group.is_po_matched,
                    total_amount=accumulated_amount,
                    invoice_date=latest_invoice_date,
                    updated_at=group.updated_at,
                )
            )

        return activity

    except Exception as err:
        raise AppException(detail=str(err)) from err


async def filterInvoices(search: str, db: AsyncSession) -> list[InvoiceResponse]:
    """Function to filter invoices based on a search query. This function queries the database to retrieve invoices that match the provided search criteria, which can include invoice ID or vendor name. It uses SQLAlchemy's AsyncSession to execute the necessary queries and returns a list of InvoiceResponse objects containing the filtered invoice data. The function also includes error handling to manage any exceptions that may arise during the database operations, ensuring that meaningful error messages are provided when issues occur."""
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
        records = result.scalars().all()
        return [InvoiceResponse.model_validate(r) for r in records]

    except Exception as err:
        raise AppException(detail=str(err)) from err


async def filterPurchaseOrders(search: str, db: AsyncSession) -> list[PurchaseOrderResponse]:
    """Function to filter purchase orders based on a search query. This function queries the database to retrieve purchase orders that match the provided search criteria, which can include purchase order ID, GL code, status, or vendor name. It uses SQLAlchemy's AsyncSession to execute the necessary queries and returns a list of PurchaseOrderResponse objects containing the filtered purchase order data. The function also includes error handling to manage any exceptions that may arise during the database operations, ensuring that meaningful error messages are provided when issues occur."""
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
        records = result.scalars().all()
        return [PurchaseOrderResponse.model_validate(r) for r in records]

    except Exception as err:
        raise AppException(detail=str(err)) from err


async def getMonthlyVolume(db: AsyncSession) -> list[MonthlyVolumeItem]:
    """Function to retrieve monthly volume statistics. This function queries the database to calculate the total volume of documents processed for each month over the past six months. It uses SQLAlchemy's AsyncSession to execute the necessary queries and returns a list of dictionaries, each containing the month and the corresponding document volume. The function also includes error handling to manage any exceptions that may arise during the database operations, ensuring that meaningful error messages are provided when issues occur."""
    try:
        now = datetime.now(UTC)
        months = [now - relativedelta(months=i) for i in range(5, -1, -1)]

        result: list[MonthlyVolumeItem] = []

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
                MonthlyVolumeItem(
                    month=dt.strftime("%b"),
                    invoices=invoice_count or 0,
                    po=po_count or 0,
                )
            )

        return result

    except Exception as err:
        raise AppException(detail=str(err)) from err


async def getMonthlyAmount(db: AsyncSession) -> list[MonthlyAmountItem]:
    """Function to retrieve monthly amount statistics. This function queries the database to calculate the total amount of documents processed for each month over the past six months. It uses SQLAlchemy's AsyncSession to execute the necessary queries and returns a list of dictionaries, each containing the month and the corresponding document amount. The function also includes error handling to manage any exceptions that may arise during the database operations, ensuring that meaningful error messages are provided when issues occur."""
    try:
        now = datetime.now(UTC)
        months = [now - relativedelta(months=i) for i in range(5, -1, -1)]

        result: list[MonthlyAmountItem] = []

        for dt in months:
            total = await db.scalar(
                select(func.sum(Invoice.total_amount)).where(
                    extract("year", Invoice.created_at) == dt.year,
                    extract("month", Invoice.created_at) == dt.month,
                )
            )

            result.append(
                MonthlyAmountItem(
                    month=dt.strftime("%b"),
                    amount=float(total or 0),
                )
            )

        return result

    except Exception as err:
        raise AppException(detail=str(err)) from err


async def getQuickStats(db: AsyncSession) -> QuickStatsResponse:
    """Function to retrieve quick statistics about documents. This function queries the database to gather quick statistics such as the number of invoices and purchase orders for the current month, the number of active associates, and the percentage change in total amount compared to the previous month. It uses SQLAlchemy's AsyncSession to execute the necessary queries and returns a dictionary containing the gathered quick statistics. The function also includes error handling to manage any exceptions that may arise during the database operations, ensuring that meaningful error messages are provided when issues occur."""
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

        return QuickStatsResponse(
            invoices_this_month=invoices_this_month or 0,
            po_this_month=po_this_month or 0,
            active_associates=active_associates or 0,
            amount_change_pct=change_pct,
        )

    except Exception as err:
        raise AppException(detail=str(err)) from err


async def getInvoiceMatchings(
    db: AsyncSession, search: str | None = None
) -> list[InvoiceMatchingResponse]:
    """Function to retrieve invoice matchings based on a search query. This function queries the database to fetch matching groups that match the provided search criteria, which can include invoice ID, purchase order ID, status, or decision. It uses SQLAlchemy's AsyncSession to execute the necessary queries and returns a list of dictionaries, each containing details of the matching groups that meet the search criteria. The function also includes error handling to manage any exceptions that may arise during the database operations, ensuring that meaningful error messages are provided when issues occur."""
    try:
        stmt = select(InvoiceMatching).order_by(InvoiceMatching.updated_at.desc())

        if search:
            # Search groups where any invoice_id or po_id matches, or by status/decision
            stmt = stmt.where(
                or_(
                    InvoiceMatching.invoices.contains([search]),
                    InvoiceMatching.pos.contains([search]),
                    cast(InvoiceMatching.status, String).ilike(f"{search}%"),
                    cast(InvoiceMatching.decision, String).ilike(f"{search}%"),
                )
            )

        result = await db.execute(stmt)
        groups = result.scalars().all()

        response: list[InvoiceMatchingResponse] = []
        for group in groups:
            # Load all invoices in this group
            invoices_detail: list[InvoiceMatchingInvoice] = []
            for invoice_id in group.invoices or []:
                inv_records = await get_data_by_any(
                    Invoice,
                    db,
                    invoice_id=invoice_id,
                )
                if inv_records:
                    inv = inv_records[0]
                    # Load vendor separately
                    vendor_records = await get_data_by_any(Vendor, db, id=inv.vendor_id)
                    vendor = vendor_records[0] if vendor_records else None
                    invoices_detail.append(
                        InvoiceMatchingInvoice(
                            invoice_id=inv.invoice_id,
                            invoice_date=inv.invoice_date,
                            due_date=inv.due_date,
                            total_amount=float(inv.total_amount or 0),
                            subtotal=float(inv.subtotal or 0),
                            tax_amount=float(inv.tax_amount or 0),
                            currency_code=inv.currency_code,
                            vendor=(
                                VendorResponse(
                                    name=vendor.name,
                                    email=vendor.email,
                                    mobile_number=vendor.mobile_number,
                                    address=vendor.address,
                                )
                                if vendor
                                else None
                            ),
                        )
                    )

            # Load all POs in this group
            pos_detail: list[InvoiceMatchingPO] = []
            for po_id in group.pos or []:
                po_records = await get_data_by_any(PurchaseOrder, db, po_id=po_id)
                if po_records:
                    po = po_records[0]
                    pos_detail.append(
                        InvoiceMatchingPO(
                            po_id=po.po_id,
                            total_amount=float(po.total_amount or 0),
                            currency_code=po.currency_code,
                            status=po.status.value,
                            ordered_date=po.ordered_date,
                        )
                    )

            response.append(
                InvoiceMatchingResponse(
                    group_id=group.id,
                    invoices=invoices_detail,
                    pos=pos_detail,
                    invoice_ids=group.invoices,
                    po_ids=group.pos,
                    # Fix: convert enum → str with .value
                    matching_status=group.status.value,
                    decision=group.decision.value if group.decision is not None else None,
                    # Fix: convert Decimal → float
                    confidence_score=float(group.confidence_score)
                    if group.confidence_score is not None
                    else None,
                    is_po_matched=group.is_po_matched,
                    command=group.command,
                    mail_to=group.mail_to,
                    mail_subject=group.mail_subject,
                    mail_body=group.mail_body,
                    matched_at=group.matched_at,
                    updated_at=group.updated_at,
                )
            )

        return response

    except Exception as err:
        raise AppException(detail=str(err)) from err


async def getInvoiceStats(db: AsyncSession) -> InvoiceStatsResponse:
    """Function to retrieve statistics related to invoices. This function queries the database to gather statistics such as the total number of invoices, counts of matching groups by status, and the total value of all invoices. It uses SQLAlchemy's AsyncSession to execute the necessary queries and returns a dictionary containing the gathered invoice statistics. The function also includes error handling to manage any exceptions that may arise during the database operations, ensuring that meaningful error messages are provided when issues occur."""
    try:
        total = await db.scalar(select(func.count(InvoiceMatching.id)))

        # Count matching groups by status
        status_counts = await db.execute(
            select(
                InvoiceMatching.status,
                func.count(InvoiceMatching.id),
            ).group_by(InvoiceMatching.status)
        )

        status_map: dict[str, int] = {row[0].value: row[1] for row in status_counts}

        total_value = await db.scalar(select(func.sum(Invoice.total_amount))) or 0

        return InvoiceStatsResponse(
            total_invoices=int(total or 0),
            approved=status_map.get("approved", 0),
            pending=status_map.get("pending", 0),
            reviewed=status_map.get("reviewed", 0),
            rejected=status_map.get("rejected", 0),
            total_value=float(total_value),
        )

    except Exception as err:
        raise AppException(detail=str(err)) from err


async def getPurchaseOrderStats(db: AsyncSession) -> PurchaseOrderStatsResponse:
    """Function to retrieve statistics related to purchase orders. This function queries the database to gather statistics such as the total number of purchase orders, counts of purchase orders by status, and the total value of all purchase orders. It uses SQLAlchemy's AsyncSession to execute the necessary queries and returns a dictionary containing the gathered purchase order statistics. The function also includes error handling to manage any exceptions that may arise during the database operations, ensuring that meaningful error messages are provided when issues occur."""
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

        return PurchaseOrderStatsResponse(
            total_pos=int(total or 0),
            pending=status_map.get("pending", 0),
            completed=status_map.get("completed", 0),
            cancelled=status_map.get("cancelled", 0),
            total_value=float(total_value),
        )

    except Exception as err:
        raise AppException(detail=str(err)) from err
