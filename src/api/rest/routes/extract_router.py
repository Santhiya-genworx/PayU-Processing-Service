"""This module defines the API routes for extracting data from invoices and purchase orders. It includes endpoints for uploading files, checking the status of extraction jobs, and retrieving the results of the extraction process. The routes are organized under the "/extract" prefix and utilize FastAPI's APIRouter for modularity. The module also interacts with a Redis queue to manage background tasks for data extraction and uses utility functions for file handling and job status management."""

import uuid
from typing import Any

from fastapi import APIRouter, File, UploadFile

from src.data.clients.redis import extract_queue
from src.schemas.docs_schema import QueueResponse
from src.tasks.payu_tasks import execute_task
from src.utils.file_upload import save_file
from src.utils.job_status import get_job_status, set_job_status

extract_router = APIRouter(prefix="/extract")


def enqueue_extract_task(file_id: str, task_type: str, filename: str, file_path: str) -> None:
    """Helper function to enqueue a task for processing uploaded files. This function takes a file ID, task type, payload, and file path as input and enqueues a task in the Redis queue for asynchronous processing. The task is executed using the execute_task function, which handles the business logic for processing the uploaded file based on the specified task type. The job status is managed using the set_job_status function to track the progress of the task. Args:   file_id (str): A unique identifier for the uploaded file. task_type (str): The type of task to be executed (e.g., "upload_invoice", "override_po"). payload (dict[str, Any]): Additional data required for processing the task. file_path (str): The path to the uploaded file that needs to be processed. Returns:    None"""
    extract_queue.enqueue(
        execute_task,
        {
            "job_id": file_id,
            "task_type": task_type,
            "filename": filename,
            "gcs_path": file_path,
        },
        job_timeout=600,
    )


@extract_router.post("/invoice")
async def extract_data_from_invoice(file: UploadFile = File(...)) -> QueueResponse:
    """Endpoint to extract data from an uploaded invoice file. This endpoint accepts a file upload, saves the file to a specified location, and enqueues a background task to process the invoice extraction. The job status is set to "processing" when the task is enqueued, and the client receives a response containing the status and a unique file ID that can be used to check the extraction status later. The file is saved using a utility function, and the background task is managed through a Redis queue. The response includes the status of the extraction process and a unique identifier for the uploaded file. Args:   file (UploadFile): The uploaded invoice file to be processed. Returns:    A dictionary containing the status of the extraction process and a unique file ID for tracking the job."""
    file_id = str(uuid.uuid4())
    file_path, _, _ = await save_file(file, "invoices")
    filename = file.filename or "upload"

    set_job_status(file_id, "processing")

    enqueue_extract_task(file_id, "extract_invoice", filename, file_path)

    return QueueResponse(status="processing", file_id=file_id)


@extract_router.post("/purchase-order")
async def extract_data_from_po(file: UploadFile = File(...)) -> QueueResponse:
    """API route for extracting data from an uploaded purchase order file. This endpoint accepts a file upload, saves the file to a specified location, and enqueues a background task to process the purchase order extraction. The job status is set to "processing" when the task is enqueued, and the client receives a response containing the status and a unique file ID that can be used to check the extraction status later."""
    file_id = str(uuid.uuid4())
    file_path, _, _ = await save_file(file, "purchase_orders")
    filename = file.filename or "upload"

    set_job_status(file_id, "processing")

    enqueue_extract_task(file_id, "extract_po", filename, file_path)

    return QueueResponse(status="processing", file_id=file_id)


@extract_router.get("/status/{file_id}")
async def get_extraction_status(file_id: str) -> dict[str, Any]:
    """API route to check the status of an extraction job using a unique file ID. This endpoint retrieves the current status of the extraction process for a given file ID by querying the job status from a Redis store. If the job is still processing, it returns a status of "processing". If the job has completed, it returns the final status and any relevant results or information associated with the job. The response is a dictionary containing the current status of the extraction job and any additional details if available. Args:   file_id (str): The unique identifier for the uploaded file whose extraction status is being checked. Returns:    A dictionary containing the current status of the extraction job and any relevant details if available."""
    job: dict[str, Any] | None = await get_job_status(file_id)

    if job is None:
        return {"status": "processing"}

    return job
