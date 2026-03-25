import asyncio
import traceback
from typing import Any, Dict, Optional, Union

from src.core.services.extraction_service import extract_text_from_document
from src.core.services.invoice_service import overrideInvoice, uploadInvoice
from src.core.services.matching_service import validateInvoicePo
from src.core.services.purchase_order_service import (
    overridePurchaseOrder,
    uploadPurchaseOrder,
)
from src.data.clients.database import AsyncSessionLocal
from src.schemas.invoice_schema import InvoiceRequest
from src.schemas.purchase_order_schema import PurchaseOrderRequest
from src.utils.job_status import set_job_status
from sqlalchemy.ext.asyncio import AsyncSession


def execute_task(data: Optional[Dict[str, Any]] = None) -> None:
    """
    Entry point for RQ worker (sync). Wraps async execution safely.
    """
    if not data:
        raise ValueError("Task data cannot be None")

    try:
        asyncio.run(_async_execute_task(data))
    except Exception as e:
        # Final fallback for any uncaught errors
        job_id = data.get("job_id", "")
        if job_id:
            set_job_status(job_id, "failed", error=str(e))
        raise


async def _async_execute_task(data: Dict[str, Any]) -> None:
    """
    Async task executor for all supported payload tasks.
    """
    task_type: str = data.get("task_type", "")
    job_id: str = data.get("job_id", "")

    async with AsyncSessionLocal() as db:
        try:
            # Dispatch to task handler
            result: Optional[Union[Dict[str, Any], None]] = await _handle_task(task_type, data, db)

            # Set job as completed with optional result
            set_job_status(job_id, "completed", result=result)

        except Exception as e:
            # Print traceback for debugging and mark job as failed
            traceback.print_exc()
            if job_id:
                set_job_status(job_id, "failed", error=str(e))
            raise


async def _handle_task(
    task_type: str,
    data: Dict[str, Any],
    db: AsyncSession
) -> Optional[Dict[str, Any]]:
    """
    Handles the actual execution of a task and returns a result if applicable.
    """
    if task_type in ("upload_invoice", "override_invoice"):
        invoice_payload = InvoiceRequest(**data["payload"])
        fn = uploadInvoice if task_type == "upload_invoice" else overrideInvoice
        await fn(invoice_payload, data["gcs_path"], db)
        return None

    elif task_type in ("upload_po", "override_po"):
        po_payload = PurchaseOrderRequest(**data["payload"])
        fn = uploadPurchaseOrder if task_type == "upload_po" else overridePurchaseOrder
        await fn(po_payload, data["gcs_path"], db)
        return None

    elif task_type == "extract_invoice":
        return await extract_text_from_document(data["gcs_path"], data["filename"], "invoice")

    elif task_type == "extract_po":
        return await extract_text_from_document(data["gcs_path"], data["filename"], "purchase_order")

    elif task_type == "validate_invoice":
        await validateInvoicePo(data["invoice_id"], data["type"])
        return None

    else:
        raise ValueError(f"Invalid task type: {task_type}")