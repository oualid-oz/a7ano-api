from uuid import UUID

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.exceptions import InvalidOrExpiredTokenException
from app.auth.repository import RefreshSessionRepository
from app.auth.schemas import DeviceInfo
from app.auth.service import AuthService
from app.core.config import settings
from app.core.database import get_db
from app.core.redis import RedisManager
from app.core.security import decode_token
from app.users.dependencies import get_user_repository, get_user_service
from app.users.models import User
from app.users.repository import UserRepository
from app.users.service import UserService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_prefix}/auth/login")


def get_device_info(request: Request) -> DeviceInfo:
    return DeviceInfo(
        user_agent=request.headers.get("User-Agent"),
        ip_address=request.client.host if request.client else None,
        fingerprint=request.headers.get("X-Device-Fingerprint"),
    )


def get_refresh_session_repository(
    session: AsyncSession = Depends(get_db),
) -> RefreshSessionRepository:
    return RefreshSessionRepository(session)


def get_auth_service(
    user_repository: UserRepository = Depends(get_user_repository),
    user_service: UserService = Depends(get_user_service),
    refresh_repository: RefreshSessionRepository = Depends(get_refresh_session_repository),
) -> AuthService:
    return AuthService(user_repository, user_service, refresh_repository)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    user_repository: UserRepository = Depends(get_user_repository),
) -> User:
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise InvalidOrExpiredTokenException()

    jti = payload.get("jti")
    if jti:
        redis = RedisManager.get()
        if await redis.exists(f"blacklist:{jti}"):
            raise InvalidOrExpiredTokenException()

    user_id = payload.get("sub")
    if not user_id:
        raise InvalidOrExpiredTokenException()

    user = await user_repository.get(UUID(user_id))
    if user is None or user.deleted_at is not None or not user.is_active:
        raise InvalidOrExpiredTokenException()

    return user


async def get_current_active_user(
    user: User = Depends(get_current_user),
) -> User:
    if user.is_locked():
        from app.auth.exceptions import AccountLockedException

        raise AccountLockedException()
    return user
