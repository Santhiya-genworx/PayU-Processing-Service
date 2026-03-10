from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    db_user:str
    db_name:str
    db_host:str
    db_password:str
    db_port: int

    gemini_api_key: str

    cloudinary_cloud_name: str
    cloudinary_api_key: str
    cloudinary_api_secret: str

    redis_host: str
    redis_port: int
    redis_db: int

    class Config:
        env_file=".env"

settings=Settings()