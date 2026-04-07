"""This module defines the API route for checking the health of the PayU Processing Service API. It includes a single endpoint that returns a simple JSON response indicating that the health check was successful. This endpoint can be used for monitoring and ensuring that the API is operational."""

from fastapi import APIRouter

from src.schemas.docs_schema import CommonResponse

health_router = APIRouter()


@health_router.get("/health", response_model=CommonResponse)
async def health_check() -> CommonResponse:
    """Endpoint to check the health of the API.
    This endpoint returns a simple JSON response indicating that the health check was successful. It can be used for monitoring and ensuring that the API is operational. The response model is defined as CommonResponse, which includes a message field to convey the status of the health check.
    Returns:
        A CommonResponse object with a message indicating the health status of the API.
    """
    return CommonResponse(message="API is healthy")
