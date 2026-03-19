from fastapi import UploadFile
import cloudinary.uploader
from google.cloud import storage
import uuid
import traceback

_client = None  
BUCKET_NAME = "gwx-stg-intern-01"
BASE_FOLDER = "payu"

async def upload(image: UploadFile, folder: str):
    file = await image.read()
    result = cloudinary.uploader.upload(file, folder=folder)

    return result["secure_url"]

def get_client():
    global _client
    if _client is None:
        _client = storage.Client()  
    return _client

async def save_file(file, folder: str):
    try:
        print("save_file called..")
        print("folder:", folder)

        bucket = get_client().bucket(BUCKET_NAME)  
        filename = file.filename or "file"
        ext = filename.split(".")[-1] if "." in filename else "bin"
        file_id = uuid.uuid4().hex
        file_path = f"{BASE_FOLDER}/{folder}/{file_id}.{ext}"

        print("uploading to:", file_path)

        blob = bucket.blob(file_path)
        content = await file.read()
        blob.upload_from_string(
            content,
            content_type=file.content_type or "application/octet-stream"
        )

        print("upload success:", file_path)
        gcs_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{file_path}"
        return file_path, ext, gcs_url

    except Exception as e:
        print("GCS ERROR")
        traceback.print_exc()
        raise

def download_from_gcs(gcs_path: str) -> bytes:
    try:
        print("⬇downloading from GCS:", gcs_path)
        bucket = get_client().bucket(BUCKET_NAME)  
        blob = bucket.blob(gcs_path)
        data = blob.download_as_bytes(timeout=60)
        print("download success:", gcs_path)
        return data
    except Exception as e:
        print("GCS DOWNLOAD ERROR")
        traceback.print_exc()
        raise

def delete_from_gcs(gcs_path: str) -> None:
    try:
        print("deleting from GCS:", gcs_path)
        bucket = get_client().bucket(BUCKET_NAME)  
        blob = bucket.blob(gcs_path)
        blob.delete()
        print("deleted:", gcs_path)
    except Exception as e:
        print(f"GCS delete failed (non-fatal): {e}")