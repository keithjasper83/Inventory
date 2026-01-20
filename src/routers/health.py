"""
Health and readiness check endpoints for the Inventory Platform.
Used for load balancer health checks and monitoring.
"""
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from src.database import SessionLocal
from src.config import settings
import redis
import os

router = APIRouter()

@router.get("/health", tags=["health"])
async def health_check():
    """
    Basic health check endpoint.
    Returns 200 OK if the application is running.
    Does not check dependencies - use /readiness for that.
    """
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "healthy",
            "app_name": settings.APP_NAME,
            "environment": settings.ENVIRONMENT
        }
    )

@router.get("/readiness", tags=["health"])
async def readiness_check():
    """
    Readiness check endpoint.
    Returns 200 OK only if all critical dependencies are available.
    Checks: Database, Redis
    """
    checks = {
        "database": False,
        "redis": False
    }
    
    # Check database
    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            checks["database"] = True
        finally:
            db.close()
    except Exception as e:
        # Only include detailed errors in development/debug mode
        if os.environ.get("ENVIRONMENT") in ["development", "debug"]:
            checks["database_error"] = str(e)
        else:
            checks["database_error"] = "Database unavailable"
    
    # Check Redis
    try:
        r = redis.from_url(settings.REDIS_URL, socket_connect_timeout=3)
        r.ping()
        checks["redis"] = True
    except Exception as e:
        # Only include detailed errors in development/debug mode
        if os.environ.get("ENVIRONMENT") in ["development", "debug"]:
            checks["redis_error"] = str(e)
        else:
            checks["redis_error"] = "Redis unavailable"
    
    # Overall status
    all_ready = checks["database"] and checks["redis"]
    
    return JSONResponse(
        status_code=status.HTTP_200_OK if all_ready else status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "status": "ready" if all_ready else "not_ready",
            "checks": checks
        }
    )
