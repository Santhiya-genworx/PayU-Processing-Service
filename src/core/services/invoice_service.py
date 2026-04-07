"""Module: invoice_service.py"""

import uuid
from typing import Any, cast

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
    append_invoice_to_group,
    append_po_to_group,
    commit_transaction,
    delete_data_by_any,
    get_data_by_any,
    get_data_by_id,
    get_matching_group_containing_invoice,
    get_matching_group_containing_po,
    insert_data,
    update_data_by_any,
    update_data_by_id,
)
from src.schemas.docs_schema import CommonResponse
from src.schemas.invoice_schema import DecisionResponse, InvoiceAction, InvoiceRequest


async def uploadInvoice(
    invoice: InvoiceRequest,
    file_url: str,
    db: AsyncSession = Depends(get_db),
) -> CommonResponse:
    """Upload a new invoice to the system. This function handles the entire process of uploading an invoice, including vendor upsert, duplicate invoice checking, inserting the invoice and its items into the database, resolving matching groups based on referenced purchase orders, and enqueuing validation tasks if necessary. The function first checks if the vendor already exists in the database and creates a new vendor record if it does not. It then checks for duplicate invoices using the invoice ID and raises a ConflictException if a duplicate is found. Next, it inserts the new invoice and its associated items into the database. After that, it determines if there are any existing matching groups that contain either the invoice or any of the referenced purchase orders. If such a group exists, it merges the new invoice into that group; otherwise, it creates a new matching group for this invoice. Finally, if the resulting group has all referenced purchase orders present in the database (i.e., is fully matched), it enqueues a validation task for that group. The function returns a message indicating that the invoice was uploaded successfully. If any errors occur during this process, they are raised as exceptions with details about the failure.   Args:   invoice (InvoiceRequest): The invoice data to be uploaded, including vendor information, invoice details, and referenced purchase orders.   file_url (str): The URL of the uploaded invoice file.   db (AsyncSession): The database session dependency for performing database operations. Returns:    A dictionary containing a message indicating that the invoice was uploaded successfully."""
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

        requested_po_ids: list[str] = list(invoice.po_id)
        existing_po_ids: set[str] = set()

        for po_id in requested_po_ids:
            po_records = await get_data_by_any(PurchaseOrder, db, po_id=po_id)
            if po_records:
                existing_po_ids.add(po_id)

        all_pos_present = len(requested_po_ids) > 0 and existing_po_ids == set(requested_po_ids)

        group = await _find_group_for_invoice(db, invoice.invoice_id, requested_po_ids)

        if group is None:
            # Create fresh group
            is_po_matched = True if all_pos_present else (None if requested_po_ids else False)
            await insert_data(
                InvoiceMatching,
                db,
                invoices=[invoice.invoice_id],
                pos=requested_po_ids,
                is_po_matched=is_po_matched,
                status=MatchingStatus.pending,
            )
            await commit_transaction(db)

            # Reload to get the auto-generated id
            group = await get_matching_group_containing_invoice(db, invoice.invoice_id)
        else:
            # Merge this invoice into the existing group
            if invoice.invoice_id not in group.invoices:
                await append_invoice_to_group(db, group.id, invoice.invoice_id)

            # Merge any new po_ids not already in the group
            for po_id in requested_po_ids:
                if po_id not in group.pos:
                    await append_po_to_group(db, group.id, po_id)

            await commit_transaction(db)

            # Re-evaluate is_po_matched for the merged group
            group = await get_data_by_id(InvoiceMatching, group.id, db)

            # Fix: guard against None before accessing .pos and .id
            if group is None:
                raise AppException(detail="Matching group not found after merge")

            # Recheck each po_id in merged group
            all_group_pos_present = True
            for po_id in group.pos or []:
                po_records = await get_data_by_any(PurchaseOrder, db, po_id=po_id)
                if not po_records:
                    all_group_pos_present = False
                    break

            new_is_po_matched = (
                True if all_group_pos_present and group.pos else (None if group.pos else False)
            )
            await update_data_by_id(InvoiceMatching, group.id, db, is_po_matched=new_is_po_matched)
            await commit_transaction(db)

            if group.pos:
                group = await get_data_by_id(InvoiceMatching, group.id, db)

        # Enqueue matching if group is ready
        if group and group.is_po_matched is True:
            _enqueue_validation(group.id, "new")

        return CommonResponse(message="Invoice uploaded successfully")

    except SQLAlchemyError as err:
        await db.rollback()
        raise AppException(detail=str(err)) from err


async def _find_group_for_invoice(
    db: AsyncSession,
    invoice_id: str,
    po_ids: list[str],
) -> "InvoiceMatching | None":
    """Find an existing matching group that contains the given invoice or any of the referenced purchase orders. This function first checks if there is a matching group that already contains the specified invoice ID. If such a group is found, it is returned immediately. If no group contains the invoice, the function then iterates through the list of referenced purchase order IDs and checks if any of them are part of an existing matching group. If a group is found that contains any of the referenced purchase orders, that group is returned. If no matching groups are found that contain either the invoice or any of the referenced purchase orders, the function returns None, indicating that a new matching group will need to be created for this invoice. The function uses database queries to efficiently locate the relevant matching groups based on the provided identifiers."""

    group: InvoiceMatching | None = await get_matching_group_containing_invoice(db, invoice_id)
    if group:
        return group

    for po_id in po_ids:
        raw = await get_matching_group_containing_po(db, po_id)
        if raw:
            return cast(InvoiceMatching, raw)  # ← fixes the no-any-return

    return None


async def overrideInvoice(
    invoice: InvoiceRequest,
    file_url: str,
    db: AsyncSession = Depends(get_db),
) -> CommonResponse:
    """Override an existing invoice with new data. This function updates the invoice record in the database with the new information provided in the InvoiceRequest, including details such as vendor information, invoice date, due date, amounts, and associated purchase orders. It also handles the upload history by recording the old and new file URLs. After updating the invoice and its items, it checks if the invoice belongs to a matching group and updates the group's PO associations accordingly. If the group becomes fully matched after the override, it enqueues a validation task for that group. The function returns a message indicating that the invoice was overridden successfully. If any errors occur during this process, they are raised as exceptions with details about the failure."""
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

        # Find and update the group that contains this invoice
        group = await get_matching_group_containing_invoice(db, invoice.invoice_id)
        if group:
            # Replace pos with the new list from the override
            new_pos = list(invoice.po_id)
            all_present = True
            for po_id in new_pos:
                po_records = await get_data_by_any(PurchaseOrder, db, po_id=po_id)
                if not po_records:
                    all_present = False
                    break
            is_po_matched = True if all_present and new_pos else (None if new_pos else False)
            await update_data_by_id(
                InvoiceMatching,
                group.id,
                db,
                pos=new_pos,
                is_po_matched=is_po_matched,
                status=MatchingStatus.pending,
            )
        else:
            # Create a new group
            new_pos = list(invoice.po_id)
            # Fix: replaced async generator expression with explicit loop
            all_present = False
            if new_pos:
                all_present = True
                for po_id in new_pos:
                    po_records = await get_data_by_any(PurchaseOrder, db, po_id=po_id)
                    if not po_records:
                        all_present = False
                        break
            is_po_matched = True if all_present and new_pos else (None if new_pos else False)
            await insert_data(
                InvoiceMatching,
                db,
                invoices=[invoice.invoice_id],
                pos=new_pos,
                is_po_matched=is_po_matched,
                status=MatchingStatus.pending,
            )
            group = await get_matching_group_containing_invoice(db, invoice.invoice_id)

        await insert_data(
            InvoiceUploadHistory,
            db,
            invoice_id=invoice.invoice_id,
            old_file_url=old_file_url,
            new_file_url=file_url,
        )

        await commit_transaction(db)

        if group and group.is_po_matched is True:
            _enqueue_validation(group.id, "override")

        return CommonResponse(message="Invoice overridden successfully")

    except SQLAlchemyError as err:
        await db.rollback()
        raise AppException(detail=str(err)) from err


async def approveInvoice(data: InvoiceAction, db: AsyncSession) -> DecisionResponse:
    """Approve an invoice based on the provided InvoiceAction data. This function retrieves the matching group that contains the specified invoice, updates the group's status to "approved", and marks all associated purchase orders in the group as "completed". If the group or any referenced purchase orders are not found, appropriate exceptions are raised. After successfully updating the statuses, the function commits the transaction and returns a response indicating that the invoice has been approved."""
    invoice_id = data.invoice_id

    group = await get_matching_group_containing_invoice(db, invoice_id)
    if not group:
        raise NotFoundException(detail=f"No matching group found for invoice {invoice_id}")

    await update_data_by_id(InvoiceMatching, group.id, db, status=MatchingStatus.approved)

    # Mark all POs in the group as completed
    for po_id in group.pos or []:
        pos = await get_data_by_any(PurchaseOrder, db, po_id=po_id)
        po = pos[0] if pos else None
        if po:
            await update_data_by_any(PurchaseOrder, db, {"po_id": po.po_id}, status="completed")

    await commit_transaction(db)
    return DecisionResponse(status="approved", invoice_id=invoice_id)


async def reviewInvoice(data: InvoiceAction, db: AsyncSession) -> DecisionResponse:
    """Review an invoice based on the provided InvoiceAction data. This function retrieves the matching group that contains the specified invoice, updates the group's status to "reviewed", and optionally updates the mail_to, mail_subject, and mail_body fields if they are provided in the InvoiceAction data. If the group is not found, a NotFoundException is raised. After successfully updating the group's status and any relevant fields, the function commits the transaction and sends an email notification if the mail_to field is set. Finally, it returns a response indicating that the invoice has been marked for review."""
    invoice_id = data.invoice_id

    group = await get_matching_group_containing_invoice(db, invoice_id)
    if not group:
        raise NotFoundException(detail=f"No matching group found for invoice {invoice_id}")

    update_fields: dict[str, Any] = {"status": MatchingStatus.reviewed}

    if data.mail_to:
        update_fields["mail_to"] = data.mail_to
    if data.mail_subject:
        update_fields["mail_subject"] = data.mail_subject
    if data.mail_body:
        update_fields["mail_body"] = data.mail_body

    await update_data_by_id(InvoiceMatching, group.id, db, **update_fields)
    await commit_transaction(db)

    # Reload group after update
    group = await get_data_by_id(InvoiceMatching, group.id, db)

    if group is not None and group.mail_to:
        await send_email(group.mail_to, group.mail_subject, group.mail_body)

    return DecisionResponse(status="reviewed", invoice_id=invoice_id)


async def rejectInvoice(data: InvoiceAction, db: AsyncSession) -> DecisionResponse:
    """Reject an invoice based on the provided InvoiceAction data. This function retrieves the matching group that contains the specified invoice, updates the group's status to "rejected", and optionally updates the mail_to, mail_subject, and mail_body fields if they are provided in the InvoiceAction data. It also marks all associated purchase orders in the group as "completed". If the group or any referenced purchase orders are not found, appropriate exceptions are raised. After successfully updating the statuses and any relevant fields, the function commits the transaction and sends an email notification if the mail_to field is set. Finally, it returns a response indicating that the invoice has been rejected."""
    invoice_id = data.invoice_id

    group = await get_matching_group_containing_invoice(db, invoice_id)
    if not group:
        raise NotFoundException(detail=f"No matching group found for invoice {invoice_id}")

    update_fields: dict[str, Any] = {"status": MatchingStatus.rejected}

    if data.mail_to:
        update_fields["mail_to"] = data.mail_to
    if data.mail_subject:
        update_fields["mail_subject"] = data.mail_subject
    if data.mail_body:
        update_fields["mail_body"] = data.mail_body

    await update_data_by_id(InvoiceMatching, group.id, db, **update_fields)

    for po_id in group.pos or []:
        pos = await get_data_by_any(PurchaseOrder, db, po_id=po_id)
        po = pos[0] if pos else None
        if po:
            await update_data_by_any(PurchaseOrder, db, {"po_id": po.po_id}, status="completed")

    await commit_transaction(db)

    group = await get_data_by_id(InvoiceMatching, group.id, db)

    if group is not None and group.mail_to:
        await send_email(group.mail_to, group.mail_subject, group.mail_body)

    return DecisionResponse(status="rejected", invoice_id=invoice_id)


async def getInvoiceDecision(invoice_id: str, db: AsyncSession) -> list[InvoiceMatching]:
    """Return the matching group(s) that contain this invoice. This function retrieves the matching group that contains the specified invoice ID from the database. If a group is found, it returns a list containing that group; otherwise, it returns an empty list. This allows clients to check the current status and details of the matching group associated with a particular invoice.  If any errors occur during the database retrieval process, an AppException is raised with details about the error."""
    group = await get_matching_group_containing_invoice(db, invoice_id)
    return [group] if group else []


def _enqueue_validation(group_id: int, operation_type: str) -> None:
    """Helper function to enqueue a validation task for a matching group. This function takes the group ID and the type of operation (e.g., "new" or "override") as parameters and enqueues a task in the match_queue to validate the invoice matching for that group. The task includes the group ID, the type of validation task, and a unique job ID for tracking. This allows for asynchronous processing of invoice validation after an invoice is uploaded or overridden. The function does not return any value and is intended to be called internally after changes are made to a matching group that requires validation. The actual validation logic will be handled by the worker that processes tasks from the match_queue, which will execute the appropriate validation steps based on the task type and group ID."""
    from src.tasks.payu_tasks import execute_task

    match_queue.enqueue(
        execute_task,
        {
            "group_id": group_id,
            "task_type": "validate_invoice",
            "type": operation_type,
            "job_id": str(uuid.uuid4()),
        },
    )
