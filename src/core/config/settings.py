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


    access_secret_key: str
    access_token_expire_minutes: int
    refresh_secret_key: str
    refresh_token_expire_days: int
    algorithm: str

    class Config:
        env_file=".env"

settings=Settings()