import uuid
from typing import Any

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
    get_data_by_any,
    insert_data,
    update_data_by_any,
)
from src.schemas.purchase_order_schema import PurchaseOrderRequest


async def uploadPurchaseOrder(
    po: PurchaseOrderRequest,
    file_url: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
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

        return {"message": f"Purchase Order {po.po_id} uploaded successfully"}

    except SQLAlchemyError as err:
        await db.rollback()
        raise AppException(detail=str(err)) from err


async def overridePurchaseOrder(
    po: PurchaseOrderRequest,
    file_url: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
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

        return {"message": f"Purchase Order {po.po_id} overridden successfully"}

    except SQLAlchemyError as err:
        await db.rollback()
        raise AppException(detail=str(err)) from err


async def _backfill_po_match(po_id: str, db: AsyncSession) -> None:
    waiting_rows = await get_data_by_any(InvoiceMatching, db, po_id=po_id, is_po_matched=False)

    if not waiting_rows:
        return

    affected_invoice_ids: set[str] = {
        row.invoice_id for row in waiting_rows if row.invoice_id is not None
    }

    await update_data_by_any(
        InvoiceMatching,
        db,
        {"po_id": po_id, "is_po_matched": False},
        is_po_matched=True,
    )

    await commit_transaction(db)

    for invoice_id in affected_invoice_ids:
        all_rows = await get_data_by_any(InvoiceMatching, db, invoice_id=invoice_id)

        if all_rows and all(row.is_po_matched for row in all_rows):
            _enqueue_validation(invoice_id, "new")


def _enqueue_validation(invoice_id: str, operation_type: str) -> None:
    from src.data.clients.redis import match_queue
    from src.tasks.payu_tasks import execute_task

    match_queue.enqueue(
        execute_task,
        {
            "invoice_id": invoice_id,
            "task_type": "validate_invoice",
            "type": operation_type,
            "job_id": str(uuid.uuid4()),
        },
        job_timeout=600,
    )
