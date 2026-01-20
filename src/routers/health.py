"""
Health and readiness check endpoints for the Inventory Platform.
Used for load balancer health checks and monitoring.
"""
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from src.database import SessionLocal
from src.config import settings
import redis

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
        db.execute("SELECT 1")
        db.close()
        checks["database"] = True
    except Exception as e:
        checks["database_error"] = str(e)
    
    # Check Redis
    try:
        r = redis.from_url(settings.REDIS_URL, socket_connect_timeout=3)
        r.ping()
        checks["redis"] = True
    except Exception as e:
        checks["redis_error"] = str(e)
    
    # Overall status
    all_ready = checks["database"] and checks["redis"]
    
    return JSONResponse(
        status_code=status.HTTP_200_OK if all_ready else status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "status": "ready" if all_ready else "not_ready",
            "checks": checks
        }
    )
