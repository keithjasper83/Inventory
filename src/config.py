import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Jules Inventory"
    # SECURITY: SECRET_KEY must be set via environment variable in production
    # Generate a secure key: python -c "import secrets; print(secrets.token_urlsafe(32))"
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "supersecretkey-CHANGE-IN-PRODUCTION")

    # Database
    # SECURITY: DATABASE_URL should be set via environment variable
    DATABASE_URL: str = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@localhost:5432/jules_inventory"
    )

    # Redis
    REDIS_URL: str = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

    # Storage (S3/MinIO)
    # SECURITY: S3 credentials should be set via environment variables in production
    S3_ENDPOINT_URL: str = os.environ.get("S3_ENDPOINT_URL", "http://localhost:9000")
    S3_ACCESS_KEY: str = os.environ.get("S3_ACCESS_KEY", "minioadmin")
    S3_SECRET_KEY: str = os.environ.get("S3_SECRET_KEY", "minioadmin")
    S3_REGION_NAME: str = os.environ.get("S3_REGION_NAME", "us-east-1")
    BUCKET_MEDIA: str = os.environ.get("BUCKET_MEDIA", "inventory-media")
    BUCKET_DOCS: str = os.environ.get("BUCKET_DOCS", "inventory-docs")

    # AI Host (Jarvis)
    JARVIS_BASE_URL: str = "" # To be loaded from config/ai_host.env
    JARVIS_HEALTH_PATH: str = "/health"

    # Security Settings
    # Token expiry in seconds (default 24 hours)
    TOKEN_EXPIRY_SECONDS: int = int(os.environ.get("TOKEN_EXPIRY_SECONDS", "86400"))
    # Maximum confidence threshold for auto-apply (0.0-1.0)
    AI_AUTO_APPLY_CONFIDENCE: float = float(os.environ.get("AI_AUTO_APPLY_CONFIDENCE", "0.95"))
    # Require manual review for AI suggestions below this threshold
    AI_MANUAL_REVIEW_THRESHOLD: float = float(os.environ.get("AI_MANUAL_REVIEW_THRESHOLD", "0.80"))

    model_config = SettingsConfigDict(
        env_file=["config/ai_host.env", ".env"],
        env_file_encoding="utf-8",
        extra="ignore"
    )

def validate_production_config():
    """
    Validate that critical security configurations are properly set for production.
    Should be called during application startup in production environments.
    """
    errors = []
    
    if settings.SECRET_KEY == "supersecretkey-CHANGE-IN-PRODUCTION":
        errors.append("SECRET_KEY is using default value. Set a secure SECRET_KEY environment variable.")
    
    if "postgres:postgres@localhost" in settings.DATABASE_URL and os.environ.get("ENVIRONMENT") == "production":
        errors.append("DATABASE_URL appears to use default credentials in production.")
    
    if settings.S3_ACCESS_KEY == "minioadmin" and os.environ.get("ENVIRONMENT") == "production":
        errors.append("S3_ACCESS_KEY is using default value in production.")
    
    if errors:
        error_msg = "\n".join(f"  - {error}" for error in errors)
        print(f"WARNING: Security configuration issues detected:\n{error_msg}")
        if os.environ.get("STRICT_CONFIG_VALIDATION", "false").lower() == "true":
            raise ValueError(f"Configuration validation failed:\n{error_msg}")
    
    return len(errors) == 0

settings = Settings()
