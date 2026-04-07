"""This module defines the API routes for extracting data from invoices and purchase orders. It includes endpoints for uploading files, checking the status of extraction jobs, and retrieving the results of the extraction process. The routes are organized under the "/extract" prefix and utilize FastAPI's APIRouter for modularity. The module also interacts with a Redis queue to manage background tasks for data extraction and uses utility functions for file handling and job status management."""

from typing import Any

from fastapi import APIRouter, File, UploadFile

from src.core.services.extraction_service import extractData, getExtractionStatus
from src.schemas.docs_schema import QueueResponse

extract_router = APIRouter(prefix="/extract")


@extract_router.post("/invoice")
async def extract_data_from_invoice(file: UploadFile = File(...)) -> QueueResponse:
    """Endpoint to extract data from an uploaded invoice file. This endpoint accepts a file upload, saves the file to a specified location, and enqueues a background task to process the invoice extraction. The job status is set to "processing" when the task is enqueued, and the client receives a response containing the status and a unique file ID that can be used to check the extraction status later. The file is saved using a utility function, and the background task is managed through a Redis queue. The response includes the status of the extraction process and a unique identifier for the uploaded file. Args:   file (UploadFile): The uploaded invoice file to be processed. Returns:    A dictionary containing the status of the extraction process and a unique file ID for tracking the job."""
    return await extractData(file, "invoices")


@extract_router.post("/purchase-order")
async def extract_data_from_po(file: UploadFile = File(...)) -> QueueResponse:
    """API route for extracting data from an uploaded purchase order file. This endpoint accepts a file upload, saves the file to a specified location, and enqueues a background task to process the purchase order extraction. The job status is set to "processing" when the task is enqueued, and the client receives a response containing the status and a unique file ID that can be used to check the extraction status later."""
    return await extractData(file, "purchase_orders")


@extract_router.get("/status/{file_id}")
async def get_extraction_status(file_id: str) -> dict[str, Any]:
    """API route to check the status of an extraction job using a unique file ID. This endpoint retrieves the current status of the extraction process for a given file ID by querying the job status from a Redis store. If the job is still processing, it returns a status of "processing". If the job has completed, it returns the final status and any relevant results or information associated with the job. The response is a dictionary containing the current status of the extraction job and any additional details if available. Args:   file_id (str): The unique identifier for the uploaded file whose extraction status is being checked. Returns:    A dictionary containing the current status of the extraction job and any relevant details if available."""
    return await getExtractionStatus(file_id)
