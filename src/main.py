"""
Main entry point for the PayU Processing Service API.
This module initializes the FastAPI application, sets up middleware, and includes API routes.
It also defines a welcome endpoint for health checks and basic connectivity testing.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.middlewares.auth import AuthMiddleware
from src.api.rest.app import app_router
from src.config.settings import settings

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

"""
Welcome endpoint to verify that the service is running.
This can be used for health checks and to confirm that the API is accessible.
Returns:
    A JSON response with a welcome message.
"""


@app.get("/")
def welcome() -> dict[str, str]:
    return {"message": "Welcome to PayU - Processing Service"}
