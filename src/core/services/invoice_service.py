import uuid
from typing import Any

from fastapi import Depends
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.rest.dependencies import get_db
from src.core.exceptions.exceptions import AppException, ConflictException, NotFoundException
from src.core.services.email_service import send_email
from src.data.clients.redis import match_queue
from src.data.models.invoice_model import Invoice, InvoiceItem
from src.data.models.matching_model import InvoiceMatching, MatchingStatus
from src.data.models.purchase_order_model import PurchaseOrder
from src.data.models.upload_history_model import InvoiceUploadHistory
from src.data.models.vendor_model import Vendor
from src.data.repositories.base_repository import (
    commit_transaction,
    delete_data_by_any,
    get_data_by_any,
    insert_data,
    update_data_by_any,
)
from src.schemas.invoice_schema import InvoiceAction, InvoiceRequest


async def uploadInvoice(
    invoice: InvoiceRequest,
    file_url: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    try:
        vendors = await get_data_by_any(Vendor, db, email=invoice.vendor.email)
        vendor = vendors[0] if vendors else None

        if vendor is None:
            await insert_data(
                Vendor,
                db,
                name=invoice.vendor.name,
                email=invoice.vendor.email,
                address=invoice.vendor.address,
                country_code=invoice.vendor.country_code,
                mobile_number=invoice.vendor.mobile_number,
                gst_number=invoice.vendor.gst_number,
                bank_name=invoice.vendor.bank_name,
                account_holder_name=invoice.vendor.account_holder_name,
                account_number=invoice.vendor.account_number,
                ifsc_code=invoice.vendor.ifsc_code,
            )
            await commit_transaction(db)

            vendors = await get_data_by_any(Vendor, db, email=invoice.vendor.email)
            vendor = vendors[0] if vendors else None

        if vendor is None:
            raise AppException(detail="Vendor creation failed")

        matched_pos: dict[str, PurchaseOrder] = {}

        for po_id in invoice.po_id:
            pos = await get_data_by_any(PurchaseOrder, db, po_id=po_id)
            po = pos[0] if pos else None

            if po:
                if po.vendor_id != vendor.id:
                    raise NotFoundException(
                        detail=f"PO {po_id} does not belong to the given vendor"
                    )
                matched_pos[po_id] = po

        existing = await get_data_by_any(Invoice, db, invoice_id=invoice.invoice_id)
        if existing:
            raise ConflictException(detail=f"Invoice {invoice.invoice_id} already exists")

        await insert_data(
            Invoice,
            db,
            invoice_id=invoice.invoice_id,
            vendor_id=vendor.id,
            invoice_date=invoice.invoice_date,
            due_date=invoice.due_date,
            currency_code=invoice.currency_code,
            subtotal=invoice.subtotal,
            tax_amount=invoice.tax_amount,
            discount_amount=invoice.discount_amount,
            total_amount=invoice.total_amount,
            file_url=file_url,
        )
        await commit_transaction(db)

        for item in invoice.invoice_items:
            await insert_data(
                InvoiceItem,
                db,
                invoice_id=invoice.invoice_id,
                item_description=item.item_description,
                quantity=item.quantity,
                unit_price=item.unit_price,
                total_price=item.total_price,
            )

        await commit_transaction(db)

        if not invoice.po_id:
            await insert_data(
                InvoiceMatching,
                db,
                invoice_id=invoice.invoice_id,
                po_id=None,
                is_po_matched=False,
                status=MatchingStatus.pending,
            )
            await commit_transaction(db)

            _enqueue_validation(invoice.invoice_id, "new")
            return {"message": "Invoice uploaded successfully"}

        all_matched = True

        for po_id in invoice.po_id:
            is_matched = po_id in matched_pos
            if not is_matched:
                all_matched = False

            await insert_data(
                InvoiceMatching,
                db,
                invoice_id=invoice.invoice_id,
                po_id=po_id,
                is_po_matched=is_matched,
                status=MatchingStatus.pending,
            )

        await commit_transaction(db)

        if all_matched:
            _enqueue_validation(invoice.invoice_id, "new")

        return {"message": "Invoice uploaded successfully"}

    except SQLAlchemyError as err:
        await db.rollback()
        raise AppException(detail=str(err)) from err


async def overrideInvoice(
    invoice: InvoiceRequest,
    file_url: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    try:
        vendors = await get_data_by_any(Vendor, db, email=invoice.vendor.email)
        vendor = vendors[0] if vendors else None

        if vendor is None:
            raise NotFoundException(detail="Vendor not found")

        existing = await get_data_by_any(Invoice, db, invoice_id=invoice.invoice_id)
        existing_invoice = existing[0] if existing else None

        if existing_invoice is None:
            raise NotFoundException(detail="Invoice not found")

        old_file_url = existing_invoice.file_url

        await update_data_by_any(
            Invoice,
            db,
            {"invoice_id": invoice.invoice_id},
            vendor_id=vendor.id,
            invoice_date=invoice.invoice_date,
            due_date=invoice.due_date,
            currency_code=invoice.currency_code,
            subtotal=invoice.subtotal,
            tax_amount=invoice.tax_amount,
            discount_amount=invoice.discount_amount or 0,
            total_amount=invoice.total_amount,
            file_url=file_url,
        )

        await delete_data_by_any(InvoiceItem, db, invoice_id=invoice.invoice_id)

        for item in invoice.invoice_items:
            await insert_data(
                InvoiceItem,
                db,
                invoice_id=invoice.invoice_id,
                item_description=item.item_description,
                quantity=item.quantity,
                unit_price=item.unit_price,
                total_price=item.total_price,
            )

        await delete_data_by_any(InvoiceMatching, db, invoice_id=invoice.invoice_id)

        for po_id in invoice.po_id:
            await insert_data(
                InvoiceMatching,
                db,
                invoice_id=invoice.invoice_id,
                po_id=po_id,
                is_po_matched=True,
                status=MatchingStatus.pending,
            )

        await insert_data(
            InvoiceUploadHistory,
            db,
            invoice_id=invoice.invoice_id,
            old_file_url=old_file_url,
            new_file_url=file_url,
        )

        await commit_transaction(db)

        _enqueue_validation(invoice.invoice_id, "override")

        return {"message": "Invoice overridden successfully"}

    except SQLAlchemyError as err:
        await db.rollback()
        raise AppException(detail=str(err)) from err


async def approveInvoice(data: InvoiceAction, db: AsyncSession) -> dict[str, Any]:
    invoice_id = data.invoice_id

    await update_data_by_any(
        InvoiceMatching,
        db,
        {"invoice_id": invoice_id},
        status=MatchingStatus.approved,
    )
    await commit_transaction(db)

    return {"status": "approved", "invoice_id": invoice_id}


async def reviewInvoice(data: InvoiceAction, db: AsyncSession) -> dict[str, Any]:
    invoice_id = data.invoice_id

    update_fields: dict[str, Any] = {"status": MatchingStatus.reviewed}

    if data.mail_to:
        update_fields["mail_to"] = data.mail_to
    if data.mail_subject:
        update_fields["mail_subject"] = data.mail_subject
    if data.mail_body:
        update_fields["mail_body"] = data.mail_body

    await update_data_by_any(InvoiceMatching, db, {"invoice_id": invoice_id}, **update_fields)
    await commit_transaction(db)

    matchings = await get_data_by_any(InvoiceMatching, db, invoice_id=invoice_id)
    matching = matchings[0] if matchings else None

    if matching is not None and matching.mail_to:
        await send_email(matching.mail_to, matching.mail_subject, matching.mail_body)

    return {"status": "reviewed", "invoice_id": invoice_id}


async def rejectInvoice(data: InvoiceAction, db: AsyncSession) -> dict[str, Any]:
    invoice_id = data.invoice_id

    update_fields: dict[str, Any] = {"status": MatchingStatus.rejected}

    if data.mail_to:
        update_fields["mail_to"] = data.mail_to
    if data.mail_subject:
        update_fields["mail_subject"] = data.mail_subject
    if data.mail_body:
        update_fields["mail_body"] = data.mail_body

    await update_data_by_any(InvoiceMatching, db, {"invoice_id": invoice_id}, **update_fields)
    await commit_transaction(db)

    matchings = await get_data_by_any(InvoiceMatching, db, invoice_id=invoice_id)
    matching = matchings[0] if matchings else None

    if matching is not None and matching.mail_to:
        await send_email(matching.mail_to, matching.mail_subject, matching.mail_body)

    return {"status": "rejected", "invoice_id": invoice_id}


def _enqueue_validation(invoice_id: str, operation_type: str) -> None:
    from src.tasks.payu_tasks import execute_task

    match_queue.enqueue(
        execute_task,
        {
            "invoice_id": invoice_id,
            "task_type": "validate_invoice",
            "type": operation_type,
            "job_id": str(uuid.uuid4()),
        },
    )
