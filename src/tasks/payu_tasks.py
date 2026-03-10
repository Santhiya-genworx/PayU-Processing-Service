import asyncio
from src.core.services.invoice_upload_service import uploadInvoice, overrideInvoice
from src.core.services.purchase_order_upload_service import uploadPurchaseOrder, overridePurchaseOrder
from src.core.services.extraction_service import extract_text_from_document
from src.schemas.invoice_schema import InvoiceRequest
from src.schemas.purchase_order_schema import PurchaseOrderRequest
from src.api.rest.dependencies import AsyncSessionLocal
from src.utils.job_status import set_job_status


def execute_task(data: dict):
    task_type = data.get("task_type")
    file_id = data.get("file_id")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_async_execute(task_type, file_id, data))
    finally:
        loop.close()

async def _async_execute(task_type: str, file_id: str, data: dict):
    try:
        async with AsyncSessionLocal() as db:

            if task_type == "upload_invoice":
                parsed = InvoiceRequest(**data["payload"])
                await uploadInvoice(parsed, data["file"], db)
                set_job_status(file_id, "completed")

            elif task_type == "override_invoice":
                parsed = InvoiceRequest(**data["payload"])
                await overrideInvoice(parsed, data["file"], db)
                set_job_status(file_id, "completed")

            elif task_type == "upload_po":
                parsed = PurchaseOrderRequest(**data["payload"])
                await uploadPurchaseOrder(parsed, data["file"], db)
                set_job_status(file_id, "completed")

            elif task_type == "override_po":
                parsed = PurchaseOrderRequest(**data["payload"])
                await overridePurchaseOrder(parsed, data["file"], db)
                set_job_status(file_id, "completed")

            elif task_type == "extract_invoice":
                result = await extract_text_from_document(
                    data["file_bytes"], data["filename"], "invoice"
                )
                set_job_status(file_id, "completed", result=result)

            elif task_type == "extract_po":
                result = await extract_text_from_document(
                    data["file_bytes"], data["filename"], "purchase order"
                )
                set_job_status(file_id, "completed", result=result)

            else:
                raise ValueError(f"Invalid task type: {task_type}")

    except Exception as e:
        if file_id:
            set_job_status(file_id, "failed", error=str(e))
        raise