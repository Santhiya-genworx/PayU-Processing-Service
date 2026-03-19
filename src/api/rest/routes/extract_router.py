import uuid
from fastapi import APIRouter, File, UploadFile
from src.utils.file_upload import save_file
from src.tasks.payu_tasks import execute_task
from src.utils.job_status import set_job_status, get_job_status
from src.data.clients.redis import extract_queue

extract_router = APIRouter(prefix="/extract")

@extract_router.post("/invoice")
async def extract_data_from_invoice(file: UploadFile = File(...)):
    file_id = str(uuid.uuid4())
    file_path, ext, gcs_url = await save_file(file, "invoices")
    filename = file.filename or "upload"

    set_job_status(file_id, "processing")

    t= extract_queue.enqueue(
        execute_task,
        {
            "job_id": file_id,
            "task_type": "extract_invoice",
            "gcs_path": file_path,
            "filename": filename
        },
        job_timeout=600  
    )
    print(t.__dict__)
    print({ "extract_queue_count": extract_queue.count })
    return {"status": "processing", "file_id": file_id}

@extract_router.post("/purchase-order")
async def extract_data_from_po(file: UploadFile = File(...)):
    file_id = str(uuid.uuid4())
    file_path, ext, gcs_url = await save_file(file, "purchase_orders")
    filename = file.filename or "upload"

    set_job_status(file_id, "processing")

    t = extract_queue.enqueue(
        execute_task,
        {
            "job_id": file_id,
            "task_type": "extract_po",
            "gcs_path": file_path,
            "filename": filename
        },
        job_timeout=600  
    )
    print(t.__dict__)
    return {"status": "processing", "file_id": file_id}

@extract_router.get("/status/{file_id}")
async def get_extraction_status(file_id: str):
    job = get_job_status(file_id)
    if job is None:
        return {"status": "processing"}
    return job