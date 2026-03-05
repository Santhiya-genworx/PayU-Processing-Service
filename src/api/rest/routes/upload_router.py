import json
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, File, Form, UploadFile
from src.api.rest.dependencies import get_db
from src.utils.file_upload import upload
from src.utils.job_status import set_job_status, get_job_status
from src.data.clients.redis import upload_queue

upload_router = APIRouter(prefix="/upload")

@upload_router.post("/invoice")
async def upload_invoice(data=Form(...), file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    file_id = str(uuid.uuid4())
    file_url = await upload(file, "invoice")
    set_job_status(file_id, "processing")
    upload_queue.enqueue(
        "src.tasks.payu_tasks.execute_task",
        {
            "file_id": file_id,
            "task_type": "upload_invoice",
            "payload": json.loads(data),
            "file": file_url,
        },
        job_timeout=300
    )
    return {"status": "processing", "file_id": file_id}

@upload_router.put("/invoice/override/{invoice_number}")
async def override_invoice(data=Form(...), file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    file_id = str(uuid.uuid4())
    file_url = await upload(file, "invoice")
    set_job_status(file_id, "processing")
    upload_queue.enqueue(
        "src.tasks.payu_tasks.execute_task",
        {
            "file_id": file_id,
            "task_type": "override_invoice",
            "payload": json.loads(data),
            "file": file_url,
        },
        job_timeout=300
    )
    return {"status": "processing", "file_id": file_id}

@upload_router.post("/purchase-order")
async def upload_purchase_orders(data=Form(...), file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    file_id = str(uuid.uuid4())
    file_url = await upload(file, "purchase order")
    set_job_status(file_id, "processing")
    upload_queue.enqueue(
        "src.tasks.payu_tasks.execute_task",
        {
            "file_id": file_id,
            "task_type": "upload_po",
            "payload": json.loads(data),
            "file": file_url,
        },
        job_timeout=300
    )
    return {"status": "processing", "file_id": file_id}

@upload_router.get("/status/{file_id}")
async def get_upload_status(file_id: str):
    job = get_job_status(file_id)
    if job is None:
        return {"status": "processing"}
    return job