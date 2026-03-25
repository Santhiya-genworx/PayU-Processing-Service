from fastapi import APIRouter

from src.api.rest.routes.docs_router import docs_router
from src.api.rest.routes.extract_router import extract_router
from src.api.rest.routes.health import health_router
from src.api.rest.routes.history_router import history_router
from src.api.rest.routes.invoice_router import invoice_router
from src.api.rest.routes.matching_router import matching_router
from src.api.rest.routes.upload_router import upload_router
from src.data.clients.database import engine, init_db
from src.observability.logging.logging_config import logger

app_router = APIRouter()

app_router.include_router(health_router)
app_router.include_router(upload_router)
app_router.include_router(extract_router)
app_router.include_router(docs_router)
app_router.include_router(history_router)
app_router.include_router(matching_router)
app_router.include_router(invoice_router)


@app_router.on_event("startup")
async def on_start() -> None:
    logger.info("App started")
    async with engine.begin():
        await init_db()
