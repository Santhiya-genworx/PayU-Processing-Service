from fastapi import APIRouter
from src.api.rest.routes.history_router import history_router
from src.api.rest.routes.docs_router import docs_router
from src.api.rest.routes.extract_router import extract_router
from src.api.rest.routes.upload_router import upload_router
from src.api.rest.routes.health import health_router
from src.data.clients.database import Base, engine

app_router = APIRouter()

app_router.include_router(health_router)
app_router.include_router(upload_router)
app_router.include_router(extract_router)
app_router.include_router(docs_router)
app_router.include_router(history_router)

@app_router.on_event("startup")
async def on_start():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)