from fastapi import FastAPI
import src.data.models
from src.api.rest.app import app_router
from fastapi.middleware.cors import CORSMiddleware
from src.core.config import cloudinary_config

app = FastAPI(title="PayU - Processing Service", version="1.0")

app.include_router(app_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"], 
)

@app.get("/")
def welcome():
    return {"message": "Welcome to PayU - Processing Service"}