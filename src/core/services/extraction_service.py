"""Module: extraction_service.py"""

import base64
import io
import os
from typing import Any

import fitz

from src.control.extractor_agent.extractor_graph import invoke_graph
from src.utils.file_upload import download_from_gcs


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
