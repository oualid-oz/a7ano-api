from typing import Any

from fastapi import APIRouter, status

from app.common.responses import success_response
from app.core.config import settings

router = APIRouter(tags=["core"])


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> dict[str, Any]:
    return success_response(
        data={
            "app": settings.app_name,
            "environment": settings.environment,
            "status": "healthy",
        }
    )


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check() -> dict[str, Any]:
    return success_response(
        data={
            "status": "ready",
        }
    )
