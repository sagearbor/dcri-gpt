from fastapi import APIRouter, status
from typing import Dict
from datetime import datetime

from app.core.config import settings

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=Dict[str, str],
    status_code=status.HTTP_200_OK,
    summary="Health Check",
    description="Check if the API is running and healthy"
)
async def health_check() -> Dict[str, str]:
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT
    }


@router.get(
    "/ready",
    response_model=Dict[str, bool],
    status_code=status.HTTP_200_OK,
    summary="Readiness Check",
    description="Check if the API is ready to handle requests"
)
async def readiness_check() -> Dict[str, bool]:
    checks = {
        "api": True,
        "database": False,  # Will be implemented when DB is added
        "redis": False,     # Will be implemented when Redis is added
    }
    
    return {
        "ready": all(checks.values()) if settings.ENVIRONMENT == "production" else True,
        **checks
    }