# import json
# import uuid
# from fastapi import APIRouter, File, Form, UploadFile
# from src.tasks.payu_tasks import execute_task
# from src.utils.file_upload import upload
# from src.utils.job_status import set_job_status, get_job_status
# from src.data.clients.redis import upload_queue

# upload_router = APIRouter(prefix="/upload")

# @upload_router.post("/invoice")
# async def upload_invoice(data=Form(...), file: UploadFile = File(...)):
#     file_id = str(uuid.uuid4())
#     file_url = await upload(file, "invoice")
#     set_job_status(file_id, "processing")
#     upload_queue.enqueue(
#         execute_task,
#         {
#             "job_id": file_id,
#             "task_type": "upload_invoice",
#             "payload": json.loads(data),
#             "file": file_url
#         }
#     )
#     return {"status": "processing", "file_id": file_id}

# @upload_router.put("/invoice/override")
# async def override_invoice(data=Form(...), file: UploadFile = File(...)):
#     file_id = str(uuid.uuid4())
#     file_url = await upload(file, "invoice")
#     set_job_status(file_id, "processing")
#     upload_queue.enqueue(
#         execute_task,
#         {
#             "job_id": file_id,
#             "task_type": "override_invoice",
#             "payload": json.loads(data),
#             "file": file_url
#         }
#     )
#     return {"status": "processing", "file_id": file_id}

# @upload_router.post("/purchase-order")
# async def upload_purchase_orders(data=Form(...), file: UploadFile = File(...)):
#     file_id = str(uuid.uuid4())
#     file_url = await upload(file, "purchase order")
#     set_job_status(file_id, "processing")
#     upload_queue.enqueue(
#         execute_task,
#         {
#             "job_id": file_id,
#             "task_type": "upload_po",
#             "payload": json.loads(data),
#             "file": file_url
#         }
#     )
#     return {"status": "processing", "file_id": file_id}

# @upload_router.put("/purchase-order/override")
# async def override_purchase_orders(data=Form(...), file: UploadFile = File(...)):
#     file_id = str(uuid.uuid4())
#     file_url = await upload(file, "purchase order")
#     set_job_status(file_id, "processing")
#     upload_queue.enqueue(
#         execute_task,
#         {
#             "job_id": file_id,
#             "task_type": "override_po",
#             "payload": json.loads(data),
#             "file": file_url
#         }
#     )
#     return {"status": "processing", "file_id": file_id}

# @upload_router.get("/status/{file_id}")
# async def get_upload_status(file_id: str):
#     job = get_job_status(file_id)
#     if job is None:
#         return {"status": "processing"}
#     return job

import json
import uuid
from fastapi import APIRouter, File, Form, UploadFile
from src.tasks.payu_tasks import execute_task
from src.utils.file_upload import save_file
from src.utils.job_status import set_job_status, get_job_status
from src.data.clients.redis import upload_queue

upload_router = APIRouter(prefix="/upload")

@upload_router.post("/invoice")
async def upload_invoice(data=Form(...), file: UploadFile = File(...)):
    file_id = str(uuid.uuid4())
    file_path, ext, gcs_url = await save_file(file, "invoices")
    set_job_status(file_id, "processing")
    upload_queue.enqueue(
        execute_task,
        {
            "job_id": file_id,
            "task_type": "upload_invoice",
            "payload": json.loads(data),
            "gcs_path": file_path
        },
        job_timeout=600  
    )
    return {"status": "processing", "file_id": file_id}


@upload_router.put("/invoice/override")
async def override_invoice(data=Form(...), file: UploadFile = File(...)):
    file_id = str(uuid.uuid4())
    file_path, ext, gcs_url = await save_file(file, "invoices")
    set_job_status(file_id, "processing")
    upload_queue.enqueue(
        execute_task,
        {
            "job_id": file_id,
            "task_type": "override_invoice",
            "payload": json.loads(data),
            "gcs_path": file_path
        },
        job_timeout=600  
    )
    return {"status": "processing", "file_id": file_id}


@upload_router.post("/purchase-order")
async def upload_purchase_orders(data=Form(...), file: UploadFile = File(...)):
    file_id = str(uuid.uuid4())
    file_path, ext, gcs_url = await save_file(file, "purchase_orders")  # ← fix folder name
    set_job_status(file_id, "processing")
    upload_queue.enqueue(
        execute_task,
        {
            "job_id": file_id,
            "task_type": "upload_po",
            "payload": json.loads(data),
            "gcs_path": file_path
        }
        ,
        job_timeout=600  
    )
    return {"status": "processing", "file_id": file_id}


@upload_router.put("/purchase-order/override")
async def override_purchase_orders(data=Form(...), file: UploadFile = File(...)):
    file_id = str(uuid.uuid4())
    file_path, ext, gcs_url = await save_file(file, "purchase_orders")  # ← fix folder name
    set_job_status(file_id, "processing")
    upload_queue.enqueue(
        execute_task,
        {
            "job_id": file_id,
            "task_type": "override_po",
            "payload": json.loads(data),
            "gcs_path": file_path
        },
        job_timeout=600  
    )
    return {"status": "processing", "file_id": file_id}


@upload_router.get("/status/{file_id}")
async def get_upload_status(file_id: str):
    job = get_job_status(file_id)
    if job is None:
        return {"status": "processing"}
    return job