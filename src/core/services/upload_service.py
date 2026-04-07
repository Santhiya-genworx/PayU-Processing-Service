"""Module: upload_service.py"""

import json
from typing import Any
import uuid

from fastapi import File, Form, UploadFile
from src.core.exceptions.exceptions import BadRequestException
from src.data.clients.redis import upload_queue
from src.tasks.payu_tasks import execute_task
from src.utils.job_status import get_job_status, set_job_status
from src.schemas.docs_schema import QueueResponse
from src.utils.file_upload import save_file

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

async def uploadData(function: str, data: str = Form(...), file: UploadFile = File(...), document_type: str = Form(...)) -> QueueResponse:
    """Function to handle the upload of data along with a file. This function takes multipart form data, including a JSON string for additional data, an uploaded file, and the document type (e.g., "invoice" or "purchase_order"). It saves the uploaded file to a specified location, sets the job status to "processing", and enqueues a background task to process the upload using the enqueue_upload_task helper function. The response includes the status of the upload process and a unique identifier for the uploaded file that can be used to track the job status later. Args:   data (str): A JSON string containing additional data related to the upload. file (UploadFile): The uploaded file to be processed. document_type (str): The type of document being uploaded (e.g., "invoice", "purchase_order"). Returns:    A QueueResponse object containing the status of the upload process and a unique file ID for tracking the job.    Raises:    BadRequestException: If there is an error during the upload process, such as file saving or task enqueuing failures, a BadRequestException is raised with details about the failure. """
    try:
        file_id = str(uuid.uuid4())
        file_path, _, _ = await save_file(file, document_type)

        set_job_status(file_id, "processing")

        enqueue_upload_task(file_id, function, json.loads(data), file_path)

        return QueueResponse(status="processing", file_id=file_id)
    
    except Exception as err:
        raise BadRequestException(f"Data upload failed: {str(err)}") from err
    
async def getUploadingStatus(file_id: str) -> dict[str, Any]:
    """Function to retrieve the status of an upload job based on the provided file ID. This function queries the job status from a Redis store using the file ID as a key. If the job is still processing, it returns a status of "processing". If the job has completed, it returns the relevant information about the job, such as success status, messages, or any additional details related to the uploaded file. Args:   file_id (str): The unique identifier for the uploaded file whose job status is being retrieved. Returns:    A dictionary containing the status of the upload job and any relevant information if the job has completed."""
    try:
        job: dict[str, Any] | None = await get_job_status(file_id)

        if job is None:
            return {"status": "processing"}

        return job

    except Exception as err:
        raise BadRequestException(f"Status check failed: {str(err)}") from err