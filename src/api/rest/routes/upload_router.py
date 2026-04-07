"""This module defines the API routes for handling file uploads related to invoices and purchase orders. The routes are organized under the "/upload" prefix and utilize FastAPI's APIRouter for modularity. Each route accepts multipart form data, including a JSON string for additional data and an uploaded file. The routes interact with a Redis queue to enqueue tasks for processing the uploaded files asynchronously. The status of each upload job is tracked using a unique file ID, which can be used to query the status of the job through a dedicated endpoint. The module also includes functionality to save the uploaded files to a specified location and manage job statuses in a Redis store."""

import json
import uuid
from typing import Any

from fastapi import APIRouter, File, Form, UploadFile

from src.data.clients.redis import upload_queue
from src.schemas.docs_schema import QueueResponse
from src.tasks.payu_tasks import execute_task
from src.utils.file_upload import save_file
from src.utils.job_status import get_job_status, set_job_status

upload_router = APIRouter(prefix="/upload")


def enqueue_upload_task(
    file_id: str, task_type: str, payload: dict[str, Any], file_path: str
) -> None:
    """Helper function to enqueue an upload task in the Redis queue. This function takes a file ID, task type, payload, and file path as input and enqueues a task to process the uploaded file. The job is set to timeout after 600 seconds (10 minutes) to ensure that long-running tasks do not block the queue indefinitely. This function abstracts the logic for enqueuing tasks and can be reused for different types of upload tasks, such as invoice uploads and purchase order uploads. Args:   file_id (str): The unique identifier for the uploaded file. task_type (str): The type of task to be executed (e.g., "upload_invoice", "override_invoice", "upload_po", "override_po"). payload (dict[str, Any]): A dictionary containing additional data related to the upload task. file_path (str): The path where the uploaded file is saved. Returns:    None"""
    upload_queue.enqueue(
        execute_task,
        {
            "job_id": file_id,
            "task_type": task_type,
            "payload": payload,
            "gcs_path": file_path,
        },
        job_timeout=600,
    )


@upload_router.post("/invoice")
async def upload_invoice(data: str = Form(...), file: UploadFile = File(...)) -> QueueResponse:
    """Endpoint to upload an invoice file along with additional data. This endpoint accepts multipart form data, including a JSON string for additional data and an uploaded file. The file is saved to a specified location, and a background task is enqueued to process the invoice upload. The job status is set to "processing" when the task is enqueued, and the client receives a response containing the status and a unique file ID that can be used to check the upload status later. The response includes the status of the upload process and a unique identifier for the uploaded file. Args:   data (str): A JSON string containing additional data related to the invoice upload. file (UploadFile): The uploaded invoice file to be processed. Returns:    A dictionary containing the status of the upload process and a unique file ID for tracking the job."""
    file_id = str(uuid.uuid4())
    file_path, _, _ = await save_file(file, "invoices")

    set_job_status(file_id, "processing")

    enqueue_upload_task(file_id, "upload_invoice", json.loads(data), file_path)

    return QueueResponse(status="processing", file_id=file_id)


@upload_router.put("/invoice/override")
async def override_invoice(data: str = Form(...), file: UploadFile = File(...)) -> QueueResponse:
    """Endpoint to override an existing invoice file along with additional data. This endpoint accepts multipart form data, including a JSON string for additional data and an uploaded file. The file is saved to a specified location, and a background task is enqueued to process the invoice override. The job status is set to "processing" when the task is enqueued, and the client receives a response containing the status and a unique file ID that can be used to check the override status later. The response includes the status of the override process and a unique identifier for the uploaded file. Args:   data (str): A JSON string containing additional data related to the invoice override. file (UploadFile): The uploaded invoice file to be processed for override. Returns:    A dictionary containing the status of the override process and a unique file ID for tracking the job."""
    file_id = str(uuid.uuid4())
    file_path, _, _ = await save_file(file, "invoices")

    set_job_status(file_id, "processing")

    enqueue_upload_task(file_id, "override_invoice", json.loads(data), file_path)

    return QueueResponse(status="processing", file_id=file_id)


@upload_router.post("/purchase-order")
async def upload_purchase_orders(
    data: str = Form(...), file: UploadFile = File(...)
) -> QueueResponse:
    """Endpoint to upload a purchase order file along with additional data. This endpoint accepts multipart form data, including a JSON string for additional data and an uploaded file. The file is saved to a specified location, and a background task is enqueued to process the purchase order upload. The job status is set to "processing" when the task is enqueued, and the client receives a response containing the status and a unique file ID that can be used to check the upload status later. The response includes the status of the upload process and a unique identifier for the uploaded file. Args:   data (str): A JSON string containing additional data related to the purchase order upload. file (UploadFile): The uploaded purchase order file to be processed. Returns:    A dictionary containing the status of the upload process and a unique file ID for tracking the job."""
    file_id = str(uuid.uuid4())
    file_path, _, _ = await save_file(file, "purchase_orders")

    set_job_status(file_id, "processing")

    enqueue_upload_task(file_id, "upload_po", json.loads(data), file_path)

    return QueueResponse(status="processing", file_id=file_id)


@upload_router.put("/purchase-order/override")
async def override_purchase_orders(
    data: str = Form(...), file: UploadFile = File(...)
) -> QueueResponse:
    """Endpoint to override an existing purchase order file along with additional data. This endpoint accepts multipart form data, including a JSON string for additional data and an uploaded file. The file is saved to a specified location, and a background task is enqueued to process the purchase order override. The job status is set to "processing" when the task is enqueued, and the client receives a response containing the status and a unique file ID that can be used to check the override status later. The response includes the status of the override process and a unique identifier for the uploaded file. Args:   data (str): A JSON string containing additional data related to the purchase order override. file (UploadFile): The uploaded purchase order file to be processed for override. Returns:    A dictionary containing the status of the override process and a unique file ID for tracking the job."""
    file_id = str(uuid.uuid4())
    file_path, _, _ = await save_file(file, "purchase_orders")

    set_job_status(file_id, "processing")

    enqueue_upload_task(file_id, "override_po", json.loads(data), file_path)

    return QueueResponse(status="processing", file_id=file_id)


@upload_router.get("/status/{file_id}")
async def get_upload_status(file_id: str) -> dict[str, Any]:
    """Endpoint to retrieve the status of an upload job based on the provided file ID. This endpoint accepts a file ID as a path parameter and uses it to query the job status from a Redis store. If the job is still processing, it returns a status of "processing". If the job has completed, it returns the relevant information about the job, such as success status, messages, or any additional details related to the uploaded file. Args:   file_id (str): The unique identifier for the uploaded file whose job status is being retrieved. Returns:    A dictionary containing the status of the upload job and any relevant information if the job has completed."""
    job: dict[str, Any] | None = await get_job_status(file_id)

    if job is None:
        return {"status": "processing"}

    return job
