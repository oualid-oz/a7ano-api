from typing import Any

from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_active_user
from app.common.responses import success_response
from app.users.dependencies import get_user_service
from app.users.models import User
from app.users.schemas import UserResponse, UserUpdate
from app.users.service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    return success_response(data=UserResponse.model_validate(current_user))


@router.patch("/me")
async def update_current_user_profile(
    data: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    service: UserService = Depends(get_user_service),
) -> dict[str, Any]:
    updated = await service.update_profile(current_user, data)
    return success_response(data=UserResponse.model_validate(updated))
