"""This module defines the API routes for handling file uploads related to invoices and purchase orders. The routes are organized under the "/upload" prefix and utilize FastAPI's APIRouter for modularity. Each route accepts multipart form data, including a JSON string for additional data and an uploaded file. The routes interact with a Redis queue to enqueue tasks for processing the uploaded files asynchronously. The status of each upload job is tracked using a unique file ID, which can be used to query the status of the job through a dedicated endpoint. The module also includes functionality to save the uploaded files to a specified location and manage job statuses in a Redis store."""

from typing import Any

from fastapi import APIRouter, File, Form, UploadFile

from src.core.services.upload_service import getUploadingStatus, uploadData
from src.schemas.docs_schema import QueueResponse

upload_router = APIRouter(prefix="/upload")


@upload_router.post("/invoice")
async def upload_invoice(data: str = Form(...), file: UploadFile = File(...)) -> QueueResponse:
    """Endpoint to upload an invoice file along with additional data. This endpoint accepts multipart form data, including a JSON string for additional data and an uploaded file. The file is saved to a specified location, and a background task is enqueued to process the invoice upload. The job status is set to "processing" when the task is enqueued, and the client receives a response containing the status and a unique file ID that can be used to check the upload status later. The response includes the status of the upload process and a unique identifier for the uploaded file. Args:   data (str): A JSON string containing additional data related to the invoice upload. file (UploadFile): The uploaded invoice file to be processed. Returns:    A dictionary containing the status of the upload process and a unique file ID for tracking the job."""
    return await uploadData("upload_invoice", data, file, "invoices")


@upload_router.put("/invoice/override")
async def override_invoice(data: str = Form(...), file: UploadFile = File(...)) -> QueueResponse:
    """Endpoint to override an existing invoice file along with additional data. This endpoint accepts multipart form data, including a JSON string for additional data and an uploaded file. The file is saved to a specified location, and a background task is enqueued to process the invoice override. The job status is set to "processing" when the task is enqueued, and the client receives a response containing the status and a unique file ID that can be used to check the override status later. The response includes the status of the override process and a unique identifier for the uploaded file. Args:   data (str): A JSON string containing additional data related to the invoice override. file (UploadFile): The uploaded invoice file to be processed for override. Returns:    A dictionary containing the status of the override process and a unique file ID for tracking the job."""
    return await uploadData("override_invoice", data, file, "invoices")


@upload_router.post("/purchase-order")
async def upload_purchase_orders(
    data: str = Form(...), file: UploadFile = File(...)
) -> QueueResponse:
    """Endpoint to upload a purchase order file along with additional data. This endpoint accepts multipart form data, including a JSON string for additional data and an uploaded file. The file is saved to a specified location, and a background task is enqueued to process the purchase order upload. The job status is set to "processing" when the task is enqueued, and the client receives a response containing the status and a unique file ID that can be used to check the upload status later. The response includes the status of the upload process and a unique identifier for the uploaded file. Args:   data (str): A JSON string containing additional data related to the purchase order upload. file (UploadFile): The uploaded purchase order file to be processed. Returns:    A dictionary containing the status of the upload process and a unique file ID for tracking the job."""
    return await uploadData("upload_po", data, file, "purchase_orders")


@upload_router.put("/purchase-order/override")
async def override_purchase_orders(
    data: str = Form(...), file: UploadFile = File(...)
) -> QueueResponse:
    """Endpoint to override an existing purchase order file along with additional data. This endpoint accepts multipart form data, including a JSON string for additional data and an uploaded file. The file is saved to a specified location, and a background task is enqueued to process the purchase order override. The job status is set to "processing" when the task is enqueued, and the client receives a response containing the status and a unique file ID that can be used to check the override status later. The response includes the status of the override process and a unique identifier for the uploaded file. Args:   data (str): A JSON string containing additional data related to the purchase order override. file (UploadFile): The uploaded purchase order file to be processed for override. Returns:    A dictionary containing the status of the override process and a unique file ID for tracking the job."""
    return await uploadData("override_po", data, file, "purchase_orders")


@upload_router.get("/status/{file_id}")
async def get_upload_status(file_id: str) -> dict[str, Any]:
    """Endpoint to retrieve the status of an upload job based on the provided file ID. This endpoint accepts a file ID as a path parameter and uses it to query the job status from a Redis store. If the job is still processing, it returns a status of "processing". If the job has completed, it returns the relevant information about the job, such as success status, messages, or any additional details related to the uploaded file. Args:   file_id (str): The unique identifier for the uploaded file whose job status is being retrieved. Returns:    A dictionary containing the status of the upload job and any relevant information if the job has completed."""
    return await getUploadingStatus(file_id)
