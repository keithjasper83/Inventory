import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Jules Inventory"
    SECRET_KEY: str = "supersecretkey" # Change in production
    ENVIRONMENT: str = "development"
    TEST_MODE: bool = os.environ.get('TEST_MODE') == '1'
    ADMIN_PASSWORD: str = "admin"
    TOKEN_EXPIRY_SECONDS: int = 86400
    AI_AUTO_APPLY_CONFIDENCE: float = 0.95
    AI_MANUAL_REVIEW_THRESHOLD: float = 0.80


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

    # AI Settings
    AI_AUTO_APPLY_CONFIDENCE: float = 0.95
    AI_MANUAL_REVIEW_THRESHOLD: float = 0.80

    # AI Host (Jarvis)
    JARVIS_BASE_URL: str = "" # To be loaded from config/ai_host.env
    JARVIS_HEALTH_PATH: str = "/health"

    model_config = SettingsConfigDict(
        env_file=["config/ai_host.env", ".env"],
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

def validate_production_config():
    """
    Validate that production environment has secure configuration.
    Raises ValueError if insecure defaults are detected.
    """
    errors = []
    
    if settings.SECRET_KEY == "supersecretkey":
        errors.append("SECRET_KEY is using default value - must be changed for production")
    
    if "postgres:postgres" in settings.DATABASE_URL and settings.ENVIRONMENT == "production":
        errors.append("DATABASE_URL contains default credentials - must be changed for production")
    
    if settings.S3_ACCESS_KEY == "minioadmin" and settings.ENVIRONMENT == "production":
        errors.append("S3_ACCESS_KEY is using default value - must be changed for production")
    
    if settings.S3_SECRET_KEY == "minioadmin" and settings.ENVIRONMENT == "production":
        errors.append("S3_SECRET_KEY is using default value - must be changed for production")
    
    if errors:
        raise ValueError(
            f"Production configuration validation failed:\n" + 
            "\n".join(f"  - {error}" for error in errors)
        )

