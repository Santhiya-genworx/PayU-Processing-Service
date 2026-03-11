import uuid
from fastapi import APIRouter, File, UploadFile
from src.utils.job_status import set_job_status, get_job_status
from src.data.clients.redis import extract_queue

extract_router = APIRouter(prefix="/extract")

@extract_router.post("/invoice")
async def extract_data_from_invoice(file: UploadFile = File(...)):
    file_id = str(uuid.uuid4())
    file_bytes = await file.read()
    filename = file.filename or "upload"

    set_job_status(file_id, "processing")

    extract_queue.enqueue(
        "src.tasks.payu_tasks.execute_task",
        {
            "file_id": file_id,
            "task_type": "extract_invoice",
            "file_bytes": file_bytes,
            "filename": filename
        },
        job_timeout=300
    )
    return {"status": "processing", "file_id": file_id}

@extract_router.post("/purchase-order")
async def extract_data_from_po(file: UploadFile = File(...)):
    file_id = str(uuid.uuid4())
    file_bytes = await file.read()
    filename = file.filename or "upload"

    set_job_status(file_id, "processing")

    extract_queue.enqueue(
        "src.tasks.payu_tasks.execute_task",
        {
            "file_id": file_id,
            "task_type": "extract_po",
            "file_bytes": file_bytes,
            "filename": filename,
        },
        job_timeout=300
    )
    return {"status": "processing", "file_id": file_id}

@extract_router.get("/status/{file_id}")
async def get_extraction_status(file_id: str):
    job = get_job_status(file_id)
    if job is None:
        return {"status": "processing"}
    return job