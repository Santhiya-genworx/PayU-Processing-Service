from fastapi import APIRouter

health_router = APIRouter()

@health_router.get("/health-check")
def health_check():
    return {"message": "PayU - Invoice Processing Service Health Check"}