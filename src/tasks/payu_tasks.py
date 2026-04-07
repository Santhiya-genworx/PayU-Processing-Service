"""module: payu_tasks.py"""

import asyncio
import traceback
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.services.extraction_service import extract_text_from_document
from src.core.services.invoice_service import overrideInvoice, uploadInvoice
from src.core.services.matching_service import validateInvoicePo
from src.core.services.purchase_order_service import (
    overridePurchaseOrder,
    uploadPurchaseOrder,
)
from src.data.clients.database import async_session_local
from src.schemas.invoice_schema import InvoiceRequest
from src.schemas.purchase_order_schema import PurchaseOrderRequest
from src.utils.job_status import set_job_status


def execute_task(data: dict[str, Any] | None = None) -> None:
    """
    Entry point for RQ worker (sync). Wraps async execution safely.
    """
    if not data:
        raise ValueError("Task data cannot be None")

    try:
        asyncio.run(_async_execute_task(data))
    except Exception as e:
        job_id = data.get("job_id", "")
        if job_id:
            set_job_status(job_id, "failed", error=str(e))
        raise


async def _async_execute_task(data: dict[str, Any]) -> None:
    """
    Async task executor for all supported payload tasks.
    """
    task_type: str = data.get("task_type", "")
    job_id: str = data.get("job_id", "")

    async with async_session_local() as db:
        try:
            result: dict[str, Any] | None | None = await _handle_task(task_type, data, db)
            set_job_status(job_id, "completed", result=result)

        except Exception as e:
            traceback.print_exc()
            if job_id:
                set_job_status(job_id, "failed", error=str(e))
            raise


async def _handle_task(
    task_type: str, data: dict[str, Any], db: AsyncSession
) -> dict[str, Any] | None:
    """
    Handles the actual execution of a task and returns a result if applicable.
    """
    if task_type in ("upload_invoice", "override_invoice"):
        invoice_payload = InvoiceRequest(**data["payload"])
        if task_type == "upload_invoice":
            await uploadInvoice(invoice_payload, data["gcs_path"], db)
        else:
            await overrideInvoice(invoice_payload, data["gcs_path"], db)
        return None

    elif task_type in ("upload_po", "override_po"):
        po_payload = PurchaseOrderRequest(**data["payload"])
        if task_type == "upload_po":
            await uploadPurchaseOrder(po_payload, data["gcs_path"], db)
        else:
            await overridePurchaseOrder(po_payload, data["gcs_path"], db)
        return None

    elif task_type == "extract_invoice":
        return await extract_text_from_document(data["gcs_path"], data["filename"], "invoice")

    elif task_type == "extract_po":
        return await extract_text_from_document(
            data["gcs_path"], data["filename"], "purchase_order"
        )

    elif task_type == "validate_invoice":
        # Now uses group_id instead of invoice_id
        group_id: int = data["group_id"]
        await validateInvoicePo(group_id, data["type"])
        return None

    else:
        raise ValueError(f"Invalid task type: {task_type}")
