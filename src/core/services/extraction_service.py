import base64
import io
import os
import fitz
from src.control.graph import invoke_graph

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
    except Exception as e:
        raise Exception(f"PDF extraction failed: {str(e)}")


async def extract_image(file_bytes: bytes) -> str:
    try:
        return base64.b64encode(file_bytes).decode("utf-8")
    except Exception as e:
        raise Exception(f"Image processing failed: {str(e)}")


async def extract_text_from_document(file_bytes: bytes, filename: str, document_type: str):
    try:
        file_type = detect_file_type(filename)
        if file_type == "unsupported":
            raise Exception(f"Unsupported file type for: {filename}")

        if file_type == "pdf":
            raw_text = await extract_pdf(file_bytes)
        elif file_type == "image":
            raw_text = await extract_image(file_bytes)
        else:
            raise Exception(f"Unsupported file type: {file_type}")

        try:
            result =  await invoke_graph(raw_text, file_type, document_type)
            return result
        except Exception as e:
            raise

    except Exception:
        raise