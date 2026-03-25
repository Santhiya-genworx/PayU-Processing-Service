import base64
import io
import os
from typing import Any

import fitz
from src.control.extractor_agent.extractor_graph import invoke_graph

from src.utils.file_upload import download_from_cloudinary


def detect_file_type(filename: str) -> str:
    extension = os.path.splitext(filename)[1].lower()
    if extension == ".pdf":
        return "pdf"
    elif extension in [".png", ".jpg", ".jpeg", ".webp"]:
        return "image"
    else:
        return "unsupported"


async def extract_pdf(file_bytes: bytes) -> str:
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
    try:
        return base64.b64encode(file_bytes).decode("utf-8")
    except Exception as err:
        raise Exception(f"Image processing failed: {str(err)}") from err


async def extract_text_from_document(
    gcs_path: str,
    filename: str,
    document_type: str,
) -> dict[str, Any]:
    try:
        file_bytes: bytes = download_from_cloudinary(gcs_path)

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
