from fastapi import FastAPI
import src.data.models
from src.api.rest.app import app_router
from fastapi.middleware.cors import CORSMiddleware
from src.core.config import cloudinary_config
from src.api.middlwares.auth import AuthMiddleware

app = FastAPI(title="PayU - Processing Service", version="1.0")

app.include_router(app_router)

app.add_middleware(AuthMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://payu-frontend-717740758627.us-east1.run.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"], 
)

@app.get("/")
def welcome():
    return {"message": "Welcome to PayU - Processing Service"}