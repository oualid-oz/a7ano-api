from typing import Any

from fastapi import APIRouter, Depends, status

from app.auth.dependencies import (
    get_auth_service,
    get_current_active_user,
    get_device_info,
    oauth2_scheme,
)
from app.auth.schemas import (
    ChangePasswordRequest,
    DeviceInfo,
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    SessionResponse,
    TokenResponse,
    VerifyEmailRequest,
)
from app.auth.service import AuthService
from app.common.responses import success_response
from app.common.schemas import SuccessResponse
from app.users.models import User
from app.users.schemas import UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=SuccessResponse[UserResponse], status_code=status.HTTP_201_CREATED)
async def register(
    data: RegisterRequest,
    device_info: DeviceInfo = Depends(get_device_info),
    service: AuthService = Depends(get_auth_service),
) -> dict[str, Any]:
    user = await service.register(data, device_info)
    return success_response(
        data=UserResponse.model_validate(user),
        message="Registration successful. Please verify your email.",
    )


@router.post("/login", response_model=SuccessResponse[TokenResponse])
async def login(
    data: LoginRequest,
    device_info: DeviceInfo = Depends(get_device_info),
    service: AuthService = Depends(get_auth_service),
) -> dict[str, Any]:
    tokens = await service.login(data, device_info)
    return success_response(data=tokens)


@router.post("/refresh", response_model=SuccessResponse[TokenResponse])
async def refresh(
    data: RefreshRequest,
    device_info: DeviceInfo = Depends(get_device_info),
    service: AuthService = Depends(get_auth_service),
) -> dict[str, Any]:
    tokens = await service.refresh(data.refresh_token, device_info)
    return success_response(data=tokens)


@router.post("/logout")
async def logout(
    data: LogoutRequest,
    access_token: str = Depends(oauth2_scheme),
    service: AuthService = Depends(get_auth_service),
) -> dict[str, Any]:
    await service.logout(data.refresh_token, access_token)
    return success_response(message="Logged out successfully.")


@router.post("/change-password")
async def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    service: AuthService = Depends(get_auth_service),
) -> dict[str, Any]:
    await service.change_password(current_user, data)
    return success_response(message="Password changed successfully.")


@router.post("/forgot-password")
async def forgot_password(
    data: ForgotPasswordRequest,
    service: AuthService = Depends(get_auth_service),
) -> dict[str, Any]:
    await service.forgot_password(str(data.email))
    return success_response(message="If the email exists, a reset link has been sent.")


@router.post("/reset-password")
async def reset_password(
    data: ResetPasswordRequest,
    service: AuthService = Depends(get_auth_service),
) -> dict[str, Any]:
    user = await service.reset_password(data)
    return success_response(
        data=UserResponse.model_validate(user),
        message="Password reset successfully.",
    )


@router.post("/verify-email")
async def verify_email(
    data: VerifyEmailRequest,
    service: AuthService = Depends(get_auth_service),
) -> dict[str, Any]:
    user = await service.verify_email(data)
    return success_response(
        data=UserResponse.model_validate(user),
        message="Email verified successfully.",
    )


@router.post("/revoke-sessions")
async def revoke_sessions(
    current_user: User = Depends(get_current_active_user),
    service: AuthService = Depends(get_auth_service),
) -> dict[str, Any]:
    await service.revoke_all_sessions(current_user.id)
    return success_response(message="All sessions revoked successfully.")


@router.get("/sessions", response_model=list[SessionResponse])
async def list_sessions(
    current_user: User = Depends(get_current_active_user),
    service: AuthService = Depends(get_auth_service),
) -> dict[str, Any]:
    sessions = await service.get_user_sessions(current_user.id)
    return success_response(data=[SessionResponse.model_validate(s) for s in sessions])
