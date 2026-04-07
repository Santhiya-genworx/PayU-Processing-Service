"""Module for defining application settings using Pydantic's BaseSettings. This module centralizes the configuration of various application parameters, including database connection details, API keys for external services, Redis configuration, JWT token settings, email server credentials, and CORS origins. The Settings class inherits from BaseSettings, allowing it to automatically read these configurations from environment variables or a .env file. This approach promotes a clean and organized way to manage application settings while keeping sensitive information secure and easily configurable across different environments (development, staging, production). The settings instance created at the end of the module can be imported and used throughout the application to access these configuration values as needed."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings class for the PayU Processing Service application. This class defines all the necessary configuration parameters required for the application to function properly, including database connection details, API keys for external services, Redis configuration, JWT token settings, email server credentials, and CORS origins. By inheriting from BaseSettings, this class can automatically load these configurations from environment variables or a .env file, providing a secure and flexible way to manage application settings across different environments."""

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
