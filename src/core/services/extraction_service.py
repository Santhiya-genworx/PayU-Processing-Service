"""Module: extraction_service.py"""

import base64
import io
import os
from typing import Any
import uuid

from fastapi import UploadFile
import fitz
from src.core.exceptions.exceptions import BadRequestException
from src.data.clients.redis import extract_queue
from src.tasks.payu_tasks import execute_task
from src.utils.job_status import get_job_status, set_job_status
from src.schemas.docs_schema import QueueResponse
from src.control.extractor_agent.extractor_graph import invoke_graph
from src.utils.file_upload import download_from_gcs, save_file

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


def detect_file_type(filename: str) -> str:
    """Function to detect the file type based on the file extension. This function takes a filename as input and checks its extension to determine whether it is a PDF or an image file. It supports common image formats such as PNG, JPG, JPEG, and WEBP. If the file extension does not match any of the supported types, it returns "unsupported". This function is used to route the document to the appropriate extraction method based on its type."""
    extension = os.path.splitext(filename)[1].lower()
    if extension == ".pdf":
        return "pdf"
    elif extension in [".png", ".jpg", ".jpeg", ".webp"]:
        return "image"
    else:
        return "unsupported"


async def extract_pdf(file_bytes: bytes) -> str:
    """Function to extract text from a PDF file. This function uses the PyMuPDF library (fitz) to open the PDF file from the provided byte stream and extract text from each page. The extracted text is concatenated and returned as a single string. If the PDF has no extractable text or if any errors occur during the extraction process, appropriate exceptions are raised with details about the failure."""
    try:
        doc = fitz.open(stream=io.BytesIO(file_bytes), filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text("text")

        text = text.strip()
        if not text:
            raise ValueError("PDF has no extractable text")

        return text
    except Exception as err:
        raise Exception(f"PDF extraction failed: {str(err)}") from err


async def extract_image(file_bytes: bytes) -> str:
    """Function to extract text from an image file. This function takes the image file as a byte stream and encodes it in base64 format, which can then be used for further processing such as OCR (Optical Character Recognition) to extract text from the image. If any errors occur during the encoding process, an exception is raised with details about the failure."""
    try:
        return base64.b64encode(file_bytes).decode("utf-8")
    except Exception as err:
        raise Exception(f"Image processing failed: {str(err)}") from err


async def extract_text_from_document(
    gcs_path: str,
    filename: str,
    document_type: str,
) -> dict[str, Any]:
    """Function to extract text from a document stored in Google Cloud Storage. This function retrieves the document from GCS using the provided path, detects the file type based on the filename, and then extracts text accordingly. For PDF files, it uses the extract_pdf function to extract text, while for image files, it uses the extract_image function to encode the image in base64 format. The extracted text or encoded image is then passed to the invoke_graph function for further processing based on the document type (e.g., invoice or purchase order). If any errors occur during this process, they are raised as exceptions with details about the failure."""
    try:
        file_bytes: bytes = download_from_gcs(gcs_path)

        file_type: str = detect_file_type(filename)

        if file_type == "unsupported":
            raise Exception(f"Unsupported file type for: {filename}")

        raw_text: str = ""
        if file_type == "pdf":
            raw_text = await extract_pdf(file_bytes)
        elif file_type == "image":
            raw_text = await extract_image(file_bytes)
        else:
            raise Exception(f"Unsupported file type: {file_type}")

        result: dict[str, Any] = await invoke_graph(raw_text, file_type, document_type)

        return result

    except Exception:
        raise

async def extractData(file: UploadFile, document_type: str) -> QueueResponse:
    """Function to handle the extraction of data from an uploaded file. This function generates a unique file ID, saves the uploaded file to a specified location, and enqueues a background task to process the file extraction. The job status is set to "processing" when the task is enqueued, and the client receives a response containing the status and a unique file ID that can be used to check the extraction status later. Args:   file (UploadFile): The uploaded file to be processed for data extraction.   document_type (str): The type of document being extracted (e.g., "invoice", "purchase_order"). Returns:    A QueueResponse object containing the status of the extraction process and a unique file ID for tracking the job. """
    try:
        file_id = str(uuid.uuid4())
        file_path, _, _ = await save_file(file, document_type)
        filename = file.filename or "upload"

        set_job_status(file_id, "processing")

        enqueue_extract_task(file_id, f"extract_{document_type}", filename, file_path)

        return QueueResponse(status="processing", file_id=file_id)
    
    except Exception as err:
        raise BadRequestException(f"Data extraction failed: {str(err)}") from err
    



async def getExtractionStatus(file_id: str) -> dict[str, Any]:
    """Function to retrieve the status of an extraction job based on the provided file ID. This function queries the job status from a Redis store using the file ID as a key. If the job is still processing, it returns a status of "processing". If the job has completed, it returns the relevant information about the job, such as success status, messages, or any additional details related to the uploaded file. Args:   file_id (str): The unique identifier for the uploaded file whose extraction status is being checked. Returns:    A dictionary containing the status of the extraction job and any relevant information if the job has completed."""
    try:
        job: dict[str, Any] | None = await get_job_status(file_id)

        if job is None:
            return {"status": "processing"}

        return job

    except Exception as err:
        raise BadRequestException(f"Status check failed: {str(err)}") from err