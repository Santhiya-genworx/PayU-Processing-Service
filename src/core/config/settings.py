from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    db_user: str
    db_name: str
    db_host: str
    db_password: str
    db_port: int
    db_url: str

    gemini_api_key: str
    groq_api_key: str

    cloudinary_cloud_name: str
    cloudinary_api_key: str
    cloudinary_api_secret: str

    redis_host: str
    redis_port: int
    redis_db: int
    redis_url: str

    access_secret_key: str
    access_token_expire_minutes: int
    refresh_secret_key: str
    refresh_token_expire_days: int
    algorithm: str

    mail_username: str
    mail_password: str
    mail_port: int
    mail_from: str
    mail_server: str

    origins: str

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()  # type: ignore
