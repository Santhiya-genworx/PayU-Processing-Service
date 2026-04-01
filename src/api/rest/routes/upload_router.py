import json
import uuid
from typing import Any

from fastapi import APIRouter, File, Form, UploadFile

from src.data.clients.redis import upload_queue
from src.tasks.payu_tasks import execute_task
from src.utils.file_upload import save_file
from src.utils.job_status import get_job_status, set_job_status

upload_router = APIRouter(prefix="/upload")


@upload_router.post("/invoice")
async def upload_invoice(data: str = Form(...), file: UploadFile = File(...)) -> dict[str, Any]:
    file_id = str(uuid.uuid4())
    file_path, ext, gcs_url = await save_file(file, "invoices")

    set_job_status(file_id, "processing")

    upload_queue.enqueue(
        execute_task,
        {
            "job_id": file_id,
            "task_type": "upload_invoice",
            "payload": json.loads(data),
            "gcs_path": file_path,
        },
        job_timeout=600,
    )

    return {"status": "processing", "file_id": file_id}


@upload_router.put("/invoice/override")
async def override_invoice(data: str = Form(...), file: UploadFile = File(...)) -> dict[str, Any]:
    file_id = str(uuid.uuid4())
    file_path, ext, gcs_url = await save_file(file, "invoices")

    set_job_status(file_id, "processing")

    upload_queue.enqueue(
        execute_task,
        {
            "job_id": file_id,
            "task_type": "override_invoice",
            "payload": json.loads(data),
            "gcs_path": file_path,
        },
        job_timeout=600,
    )

    return {"status": "processing", "file_id": file_id}


@upload_router.post("/purchase-order")
async def upload_purchase_orders(
    data: str = Form(...), file: UploadFile = File(...)
) -> dict[str, Any]:
    file_id = str(uuid.uuid4())
    file_path, ext, gcs_url = await save_file(file, "purchase_orders")

    set_job_status(file_id, "processing")

    upload_queue.enqueue(
        execute_task,
        {
            "job_id": file_id,
            "task_type": "upload_po",
            "payload": json.loads(data),
            "gcs_path": file_path,
        },
        job_timeout=600,
    )

    return {"status": "processing", "file_id": file_id}


@upload_router.put("/purchase-order/override")
async def override_purchase_orders(
    data: str = Form(...), file: UploadFile = File(...)
) -> dict[str, Any]:
    file_id = str(uuid.uuid4())
    file_path, ext, gcs_url = await save_file(file, "purchase_orders")

    set_job_status(file_id, "processing")

    upload_queue.enqueue(
        execute_task,
        {
            "job_id": file_id,
            "task_type": "override_po",
            "payload": json.loads(data),
            "gcs_path": file_path,
        },
        job_timeout=600,
    )

    return {"status": "processing", "file_id": file_id}


@upload_router.get("/status/{file_id}")
async def get_upload_status(file_id: str) -> dict[str, Any]:
    job: dict[str, Any] | None = await get_job_status(file_id)

    if job is None:
        return {"status": "processing"}

    return job
