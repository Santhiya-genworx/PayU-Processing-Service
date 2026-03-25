from __future__ import annotations

import traceback
import uuid
from typing import Any

import cloudinary
import cloudinary.api
import cloudinary.uploader
from fastapi import UploadFile
from google.cloud import storage
from google.cloud.storage import Client
import src.core.config.cloudinary_config 

from src.observability.logging.logging_config import logger

_client: Client | None = None

BUCKET_NAME = "gwx-stg-intern-01"
BASE_FOLDER = "payu"


def get_client() -> Client:
    global _client
    if _client is None:
        _client = storage.Client()
    return _client


async def save_file(file: UploadFile, folder: str) -> tuple[str, str, str]:
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
    try:
        bucket = get_client().bucket(BUCKET_NAME)
        blob = bucket.blob(gcs_path)

        data: bytes = blob.download_as_bytes(timeout=60)

        return data

    except Exception:
        traceback.print_exc()
        raise


def delete_from_gcs(gcs_path: str) -> None:
    try:
        bucket = get_client().bucket(BUCKET_NAME)
        blob = bucket.blob(gcs_path)
        blob.delete()
    except Exception as e:
        logger.error(f"GCS delete failed (non-fatal): {e}")


async def upload(image: UploadFile, folder: str) -> str:
    file_bytes: bytes = await image.read()

    result: dict[str, Any] = cloudinary.uploader.upload(file_bytes, folder=folder)

    return str(result["secure_url"])


async def save_file_cloudinary(file: UploadFile, folder: str) -> tuple[str, str, str]:
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
    try:
        cloudinary.uploader.destroy(public_id, resource_type="raw")
    except Exception as e:
        logger.error(f"Cloudinary delete failed (non-fatal): {e}")
