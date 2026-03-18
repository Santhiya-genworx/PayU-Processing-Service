# import asyncio
# from src.core.services.matching_service import validateInvoicePo
# from src.core.services.invoice_service import uploadInvoice, overrideInvoice
# from src.core.services.purchase_order_service import uploadPurchaseOrder, overridePurchaseOrder
# from src.core.services.extraction_service import extract_text_from_document
# from src.schemas.invoice_schema import InvoiceRequest
# from src.schemas.purchase_order_schema import PurchaseOrderRequest
# from src.api.rest.dependencies import AsyncSessionLocal
# from src.utils.job_status import set_job_status

# def execute_task(data: dict | None = None):
#     task_type = data.get("task_type")
#     job_id = data.get("job_id")
#     print("execute task........")
#     loop = asyncio.new_event_loop()
#     try:
#         asyncio.set_event_loop(loop)
#         loop.run_until_complete(_async_execute(task_type, job_id, data or {}))
#     finally:
#         loop.close()

# async def _async_execute(task_type: str, job_id: str, data: dict):
#     try:
#         async with AsyncSessionLocal() as db:

#             if task_type == "upload_invoice":
#                 parsed = InvoiceRequest(**data["payload"])
#                 await uploadInvoice(parsed, data["file"], db)
#                 set_job_status(job_id, "completed")

#             elif task_type == "override_invoice":
#                 parsed = InvoiceRequest(**data["payload"])
#                 await overrideInvoice(parsed, data["file"], db)
#                 set_job_status(job_id, "completed")

#             elif task_type == "upload_po":
#                 parsed = PurchaseOrderRequest(**data["payload"])
#                 await uploadPurchaseOrder(parsed, data["file"], db)
#                 set_job_status(job_id, "completed")

#             elif task_type == "override_po":
#                 parsed = PurchaseOrderRequest(**data["payload"])
#                 await overridePurchaseOrder(parsed, data["file"], db)
#                 set_job_status(job_id, "completed")

#             elif task_type == "extract_invoice":
#                 result = await extract_text_from_document(
#                     data["file_bytes"], data["filename"], "invoice"
#                 )
#                 set_job_status(job_id, "completed", result=result)

#             elif task_type == "extract_po":
#                 print("extract po............")
#                 result = await extract_text_from_document(
#                     data["file_bytes"], data["filename"], "purchase_order"
#                 )
#                 set_job_status(job_id, "completed", result=result)
            
#             elif task_type == "validate_invoice":
#                 await validateInvoicePo(data["invoice_id"], data["type"])

#             else:
#                 raise ValueError(f"Invalid task type: {task_type}")

#     except Exception as e:
#         if job_id:
#             set_job_status(job_id, "failed", error=str(e))
#         raise

import asyncio
import traceback
from src.core.services.matching_service import validateInvoicePo
from src.core.services.invoice_service import uploadInvoice, overrideInvoice
from src.core.services.purchase_order_service import uploadPurchaseOrder, overridePurchaseOrder
from src.core.services.extraction_service import extract_text_from_document
from src.schemas.invoice_schema import InvoiceRequest
from src.schemas.purchase_order_schema import PurchaseOrderRequest
from src.api.rest.dependencies import AsyncSessionLocal
from src.utils.job_status import set_job_status


def execute_task(data: dict | None = None):
    task_type = data.get("task_type")
    job_id = data.get("job_id")
    print("execute task........", task_type, job_id)
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_async_execute(task_type, job_id, data or {}))
    finally:
        loop.close()


async def _async_execute(task_type: str, job_id: str, data: dict):
    try:
        async with AsyncSessionLocal() as db:

            if task_type == "upload_invoice":
                parsed = InvoiceRequest(**data["payload"])
                await uploadInvoice(parsed, data["gcs_path"], db)
                set_job_status(job_id, "completed")

            elif task_type == "override_invoice":
                parsed = InvoiceRequest(**data["payload"])
                await overrideInvoice(parsed, data["gcs_path"], db)
                set_job_status(job_id, "completed")

            elif task_type == "upload_po":
                parsed = PurchaseOrderRequest(**data["payload"])
                await uploadPurchaseOrder(parsed, data["gcs_path"], db)
                set_job_status(job_id, "completed")

            elif task_type == "override_po":
                parsed = PurchaseOrderRequest(**data["payload"])
                await overridePurchaseOrder(parsed, data["gcs_path"], db)
                set_job_status(job_id, "completed")

            elif task_type == "extract_invoice":
                print("extract invoice............")
                result = await extract_text_from_document(
                    data["gcs_path"], data["filename"], "invoice"   # ← gcs_path instead of file_bytes
                )
                set_job_status(job_id, "completed", result=result)

            elif task_type == "extract_po":
                print("extract po............")
                result = await extract_text_from_document(
                    data["gcs_path"], data["filename"], "purchase_order"  # ← gcs_path instead of file_bytes
                )
                set_job_status(job_id, "completed", result=result)

            elif task_type == "validate_invoice":
                await validateInvoicePo(data["invoice_id"], data["type"])

            else:
                raise ValueError(f"Invalid task type: {task_type}")

    except Exception as e:
        traceback.print_exc()
        if job_id:
            set_job_status(job_id, "failed", error=str(e))
        raise