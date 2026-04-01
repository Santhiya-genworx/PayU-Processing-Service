from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config.settings import settings
from src.api.middlewares.auth import AuthMiddleware
from src.api.rest.app import app_router

app = FastAPI(title="PayU - Processing Service", version="1.0")

app.include_router(app_router)

app.add_middleware(AuthMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def welcome() -> dict[str, str]:
    return {"message": "Welcome to PayU - Processing Service"}
