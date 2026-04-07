"""module: file_upload.py"""

import traceback
import uuid
from typing import Any

import cloudinary
import cloudinary.api
import cloudinary.uploader
from fastapi import UploadFile
from google.cloud import storage
from google.cloud.storage import Client

from src.core.exceptions.exceptions import BadRequestException
from src.observability.logging.logging_config import logger

_client: Client | None = None

BUCKET_NAME = "gwx-stg-intern-01"
BASE_FOLDER = "payu"


def get_client() -> Client:
    """Get a singleton instance of the Google Cloud Storage client. This function checks if a global client instance already exists; if it does, it returns that instance. If not, it creates a new instance of the storage.Client, assigns it to the global variable, and then returns it. This approach ensures that only one instance of the storage client is created and reused throughout the application, which can help improve performance and reduce resource usage when interacting with Google Cloud Storage."""
    global _client
    if _client is None:
        _client = storage.Client()
    return _client


async def save_file(file: UploadFile, folder: str) -> tuple[str, str, str]:
    """Save an uploaded file to Google Cloud Storage. This function takes an UploadFile object and a folder name as input, generates a unique file path based on the provided folder and a UUID, and uploads the file content to the specified Google Cloud Storage bucket. It returns a tuple containing the file path in the bucket, the file extension, and the public URL of the uploaded file. The function handles any exceptions that may occur during the upload process and logs them for debugging purposes."""
    try:
        bucket = get_client().bucket(BUCKET_NAME)

        filename = file.filename or "file"
        ext = filename.split(".")[-1] if "." in filename else "bin"

        file_id = uuid.uuid4().hex
        file_path = f"{BASE_FOLDER}/{folder}/{file_id}.{ext}"

        blob = bucket.blob(file_path)

        content: bytes = await file.read()

        blob.upload_from_string(
            content,
            content_type=file.content_type or "application/octet-stream",
        )

        gcs_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{file_path}"

        return file_path, ext, gcs_url

    except Exception:
        traceback.print_exc()
        raise


def download_from_gcs(gcs_path: str) -> bytes:
    """Download a file from Google Cloud Storage. This function takes the path of the file in the Google Cloud Storage bucket as input, retrieves the file content as bytes, and returns it. It handles any exceptions that may occur during the download process and logs them for debugging purposes."""
    try:
        bucket = get_client().bucket(BUCKET_NAME)
        blob = bucket.blob(gcs_path)

        data: bytes = blob.download_as_bytes(timeout=60)

        return data

    except Exception:
        traceback.print_exc()
        raise


def delete_from_gcs(gcs_path: str) -> None:
    """Delete a file from Google Cloud Storage. This function takes the path of the file in the Google Cloud Storage bucket as input and attempts to delete the file. If the deletion fails, it logs an error message but does not raise an exception, allowing the application to continue functioning even if the file cannot be deleted. This approach is useful for handling cases where cleanup of files may fail without impacting the overall functionality of the application."""
    try:
        bucket = get_client().bucket(BUCKET_NAME)
        blob = bucket.blob(gcs_path)
        blob.delete()
    except BadRequestException as err:
        logger.exception(f"GCS delete failed (non-fatal): {err}")


async def upload(image: UploadFile, folder: str) -> str:
    """Upload a file to Cloudinary. This function takes an UploadFile object and a folder name as input, reads the file content as bytes, and uploads it to Cloudinary under the specified folder. It returns the secure URL of the uploaded file. The function handles any exceptions that may occur during the upload process and logs them for debugging purposes."""
    file_bytes: bytes = await image.read()

    result: dict[str, Any] = cloudinary.uploader.upload(file_bytes, folder=folder)

    return str(result["secure_url"])


async def save_file_cloudinary(file: UploadFile, folder: str) -> tuple[str, str, str]:
    """Save an uploaded file to Cloudinary. This function takes an UploadFile object and a folder name as input, generates a unique file path based on the provided folder and a UUID, and uploads the file content to Cloudinary. It returns a tuple containing the file path in Cloudinary, the file extension, and the secure URL of the uploaded file. The function handles any exceptions that may occur during the upload process and logs them for debugging purposes."""
    try:
        filename = file.filename or "file"
        ext = filename.split(".")[-1] if "." in filename else "bin"

        file_id = uuid.uuid4().hex
        public_id = f"{BASE_FOLDER}/{folder}/{file_id}"

        content: bytes = await file.read()

        result: dict[str, Any] = cloudinary.uploader.upload(
            content,
            public_id=public_id,
            resource_type="raw",
            overwrite=True,
        )

        file_path: str = str(result["public_id"])
        secure_url: str = str(result["secure_url"])

        return file_path, ext, secure_url

    except Exception:
        traceback.print_exc()
        raise


def download_from_cloudinary(public_id: str) -> bytes:
    """Download a file from Cloudinary. This function takes the public ID of the file in Cloudinary as input, retrieves the file content as bytes, and returns it. It handles any exceptions that may occur during the download process and logs them for debugging purposes."""
    try:
        import urllib.request

        resource: dict[str, Any] = cloudinary.api.resource(public_id, resource_type="raw")

        url: str = str(resource["secure_url"])

        with urllib.request.urlopen(url) as response:
            data: bytes = response.read()

        return data

    except Exception:
        traceback.print_exc()
        raise


def delete_from_cloudinary(public_id: str) -> None:
    """Delete a file from Cloudinary. This function takes the public ID of the file in Cloudinary as input and attempts to delete the file. If the deletion fails, it logs an error message but does not raise an exception, allowing the application to continue functioning even if the file cannot be deleted. This approach is useful for handling cases where cleanup of files may fail without impacting the overall functionality of the application."""
    try:
        cloudinary.uploader.destroy(public_id, resource_type="raw")
    except BadRequestException as err:
        logger.exception(f"Cloudinary delete failed (non-fatal): {err}")
