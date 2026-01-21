import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Jules Inventory"
    SECRET_KEY: str = "supersecretkey" # Change in production
    ENVIRONMENT: str = "development"

    # Database
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/jules_inventory"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Storage (S3/MinIO)
    S3_ENDPOINT_URL: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_REGION_NAME: str = "us-east-1"
    BUCKET_MEDIA: str = "inventory-media"
    BUCKET_DOCS: str = "inventory-docs"

    # AI Host (Jarvis)
    JARVIS_BASE_URL: str = "" # To be loaded from config/ai_host.env
    JARVIS_HEALTH_PATH: str = "/health"

    model_config = SettingsConfigDict(
        env_file=["config/ai_host.env", ".env"],
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
