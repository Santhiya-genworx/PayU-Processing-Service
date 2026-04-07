"""Module: purchase_order_service.py"""

import uuid

from fastapi import Depends
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.rest.dependencies import get_db
from src.core.exceptions.exceptions import (
    AppException,
    BadRequestException,
    ConflictException,
    NotFoundException,
)
from src.data.models.matching_model import InvoiceMatching
from src.data.models.purchase_order_model import (
    OrderedItems,
    POStatus,
    PurchaseOrder,
)
from src.data.models.upload_history_model import PurchaseOrderUploadHistory
from src.data.models.vendor_model import Vendor
from src.data.repositories.base_repository import (
    commit_transaction,
    delete_data_by_any,
    get_all_matching_groups_containing_po,
    get_data_by_any,
    insert_data,
    update_data_by_any,
    update_data_by_id,
)
from src.schemas.docs_schema import CommonResponse
from src.schemas.purchase_order_schema import PurchaseOrderRequest


async def uploadPurchaseOrder(
    po: PurchaseOrderRequest,
    file_url: str,
    db: AsyncSession = Depends(get_db),
) -> CommonResponse:
    """Upload a new purchase order, insert into DB, then backfill any matching groups that reference this po_id to is_po_matched = True if all POs are now present. This function first checks if the vendor associated with the purchase order already exists in the database and creates a new vendor record if necessary. It then checks for duplicate purchase orders to prevent overwriting existing data. If the purchase order is unique, it inserts the new purchase order and its associated ordered items into the database. After successfully inserting the purchase order, it calls a helper function to backfill any matching groups that reference this po_id, which will update those groups to indicate that the PO has been matched and enqueue them for validation. If any errors occur during this process, appropriate exceptions are raised with details about the failure.   This function ensures that any pending matches that were waiting for this PO to be uploaded are now processed accordingly."""
    try:
        vendors = await get_data_by_any(Vendor, db, email=po.vendor.email)
        vendor = vendors[0] if vendors else None

        if vendor is None:
            await insert_data(
                Vendor,
                db,
                name=po.vendor.name,
                email=po.vendor.email,
                address=po.vendor.address,
                country_code=po.vendor.country_code,
                mobile_number=po.vendor.mobile_number,
                gst_number=po.vendor.gst_number,
                bank_name=po.vendor.bank_name,
                account_holder_name=po.vendor.account_holder_name,
                account_number=po.vendor.account_number,
                ifsc_code=po.vendor.ifsc_code,
            )
            await commit_transaction(db)
            vendors = await get_data_by_any(Vendor, db, email=po.vendor.email)
            vendor = vendors[0] if vendors else None

        if vendor is None:
            raise AppException(detail="Vendor creation failed")

        existing_pos = await get_data_by_any(PurchaseOrder, db, po_id=po.po_id)
        if existing_pos:
            raise ConflictException(detail=f"Purchase Order {po.po_id} already exists")

        await insert_data(
            PurchaseOrder,
            db,
            po_id=po.po_id,
            vendor_id=vendor.id,
            gl_code=po.gl_code,
            currency_code=po.currency_code,
            total_amount=po.total_amount,
            ordered_date=po.ordered_date,
            status=POStatus.pending,
            file_url=file_url,
        )

        for item in po.ordered_items:
            await insert_data(
                OrderedItems,
                db,
                po_id=po.po_id,
                item_description=item.item_description,
                quantity=item.quantity,
                unit_price=item.unit_price,
                total_price=item.total_price,
            )

        await commit_transaction(db)

        await _backfill_po_match(po.po_id, db)

        return CommonResponse(message=f"Purchase Order {po.po_id} uploaded successfully")

    except SQLAlchemyError as err:
        await db.rollback()
        raise AppException(detail=str(err)) from err


async def overridePurchaseOrder(
    po: PurchaseOrderRequest,
    file_url: str,
    db: AsyncSession = Depends(get_db),
) -> CommonResponse:
    """Override an existing PO, update DB, then update any matching groups that reference this po_id to is_po_matched = True and enqueue for matching. Similar to uploadPurchaseOrder but with additional checks to ensure the PO exists and belongs to the correct vendor, and it also records the upload history for audit purposes. After updating the PO, it backfills any matching groups that reference this po_id to ensure they are processed now that the PO has been overridden.  This function ensures that any pending matches that were waiting for this PO to be uploaded are now processed accordingly."""
    try:
        vendors = await get_data_by_any(Vendor, db, email=po.vendor.email)
        vendor = vendors[0] if vendors else None

        if vendor is None:
            raise NotFoundException(detail="Vendor not found")

        existing_pos = await get_data_by_any(PurchaseOrder, db, po_id=po.po_id)
        existing_po = existing_pos[0] if existing_pos else None

        if existing_po is None:
            raise NotFoundException(detail="Purchase Order not found")

        if existing_po.vendor_id != vendor.id:
            raise BadRequestException(detail="PO does not belong to given vendor")

        old_file_url = existing_po.file_url

        await update_data_by_any(
            PurchaseOrder,
            db,
            {"po_id": po.po_id},
            vendor_id=vendor.id,
            gl_code=po.gl_code,
            total_amount=po.total_amount,
            ordered_date=po.ordered_date,
            file_url=file_url,
        )

        await delete_data_by_any(OrderedItems, db, po_id=po.po_id)

        for item in po.ordered_items:
            await insert_data(
                OrderedItems,
                db,
                po_id=po.po_id,
                item_description=item.item_description,
                quantity=item.quantity,
                unit_price=item.unit_price,
                total_price=item.total_price,
            )

        await insert_data(
            PurchaseOrderUploadHistory,
            db,
            po_id=po.po_id,
            old_file_url=old_file_url,
            new_file_url=file_url,
        )

        await commit_transaction(db)

        await _backfill_po_match(po.po_id, db)

        return CommonResponse(message=f"Purchase Order {po.po_id} overridden successfully")

    except SQLAlchemyError as err:
        await db.rollback()
        raise AppException(detail=str(err)) from err


async def _backfill_po_match(po_id: str, db: AsyncSession) -> None:
    """Helper function to backfill matching groups that reference the given po_id. This function checks for any matching groups that contain the specified po_id in their list of associated POs and updates those groups to indicate that the PO has now been matched. It then enqueues a background task to validate the matching group, which will determine the final matching decision based on the presence of all associated invoices and POs. This ensures that any pending matches that were waiting for this PO to be uploaded are now processed accordingly."""
    groups = await get_all_matching_groups_containing_po(db, po_id)

    for group in groups:
        # Skip groups already matched/processing
        if group.is_po_matched is True:
            continue

        # Check if every po_id in this group now exists in the DB
        all_present = True
        for gpo_id in group.pos or []:
            po_records = await get_data_by_any(PurchaseOrder, db, po_id=gpo_id)
            if not po_records:
                all_present = False
                break

        if all_present and group.pos:
            await update_data_by_id(InvoiceMatching, group.id, db, is_po_matched=True)
            await commit_transaction(db)
            _enqueue_validation(group.id, "new")


def _enqueue_validation(group_id: int, operation_type: str) -> None:
    """Enqueue a background task to validate the matching group now that all POs are present. The task will be picked up by a worker and will execute the necessary logic to determine the matching decision for the group based on its invoices and POs.   The operation_type parameter indicates whether this validation is triggered by a new upload or an override, which can be used to customize the validation logic if needed.  This function does not return any value but ensures that the validation process is initiated for the specified matching group."""
    from src.data.clients.redis import match_queue
    from src.tasks.payu_tasks import execute_task

    match_queue.enqueue(
        execute_task,
        {
            "group_id": group_id,
            "task_type": "validate_invoice",
            "type": operation_type,
            "job_id": str(uuid.uuid4()),
        },
        job_timeout=600,
    )
