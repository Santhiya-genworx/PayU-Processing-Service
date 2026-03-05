# import base64
# import os
# import fitz
# import aiohttp
# from src.control.graph import invoke_graph

# def detect_file_type(file_path: str) -> str:
#     extension = os.path.splitext(file_path)[1].lower()
#     if extension == ".pdf":
#         return "pdf"
#     elif extension in [".png", ".jpg", ".jpeg", ".webp"]:
#         return "image"
#     else:
#         return "unsupported"
    
# async def extract_pdf(file_path: str) -> str:
#     try:
#         file_bytes = None
#         with open(file_path, "rb") as f:
#             file_bytes = f.read()

#         doc = fitz.open(stream=file_bytes, filetype="pdf")
#         text = ""
#         for page in doc:
#             text += page.get_text("text")

#         text = text.strip()
#         if not text:
#             raise ValueError("Empty PDF content")

#         return text
#     except Exception as e:
#         raise Exception(f"PDF extraction failed: {str(e)}")

# async def extract_image(file_path: str) -> str:
#     try:
#         file_bytes = None
#         with open(file_path, "rb") as f:
#             file_bytes = f.read()
#         return base64.b64encode(file_bytes).decode("utf-8")

#     except Exception as e:
#         raise Exception(f"Image Processing failed: {str(e)}")

# async def extract_text_from_document(file_path: str, document_type: str):
#     try:
#         print(file_path)
#         file_type = detect_file_type(file_path)
#         raw_text = ""
        
#         if file_type == "pdf":
#             raw_text = await extract_pdf(file_path)
#         elif file_type == "image":
#             raw_text = await extract_image(file_path)
#         else:
#             raise Exception(f"Unsupported file type: {file_type}")

#         return await invoke_graph(raw_text, file_type, document_type)

#     except Exception as e:
#         raise Exception(f"Document extraction failed: {str(e)}")
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
    """Extract text from PDF bytes using PyMuPDF."""
    try:
        doc = fitz.open(stream=io.BytesIO(file_bytes), filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text("text")

        text = text.strip()
        if not text:
            raise ValueError("PDF has no extractable text (may be scanned/image-based)")

        return text
    except Exception as e:
        raise Exception(f"PDF extraction failed: {str(e)}")


async def extract_image(file_bytes: bytes) -> str:
    """Base64-encode image bytes for downstream processing."""
    try:
        return base64.b64encode(file_bytes).decode("utf-8")
    except Exception as e:
        raise Exception(f"Image processing failed: {str(e)}")


async def extract_text_from_document(file_bytes: bytes, filename: str, document_type: str):
    """
    Accept raw file bytes directly — no download required.
    Detect type from filename, extract content, pass to graph.
    """
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

        return await invoke_graph(raw_text, file_type, document_type)

    except Exception as e:
        raise Exception(f"Document extraction failed: {str(e)}")