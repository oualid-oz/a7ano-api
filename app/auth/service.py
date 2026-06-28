from datetime import UTC, datetime, timedelta
from hashlib import sha256
from secrets import token_urlsafe
from uuid import UUID, uuid4

from app.auth.exceptions import (
    AccountLockedException,
    EmailVerificationTokenInvalidException,
    InvalidCredentialsException,
    InvalidOrExpiredTokenException,
    PasswordResetTokenInvalidException,
    SessionExpiredException,
)
from app.auth.models import RefreshSession
from app.auth.repository import RefreshSessionRepository
from app.auth.schemas import (
    ChangePasswordRequest,
    DeviceInfo,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    VerifyEmailRequest,
)
from app.core.config import settings
from app.core.redis import RedisManager
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.users.models import User
from app.users.repository import UserRepository
from app.users.schemas import UserCreate
from app.users.service import UserService


class AuthService:
    def __init__(
        self,
        user_repository: UserRepository,
        user_service: UserService,
        refresh_repository: RefreshSessionRepository,
    ) -> None:
        self._user_repository = user_repository
        self._user_service = user_service
        self._refresh_repository = refresh_repository

    async def register(self, data: RegisterRequest, device_info: DeviceInfo) -> User:
        user_data = UserCreate(email=data.email, password=data.password, full_name=data.full_name)
        user = await self._user_service.create(user_data)
        await self._send_email_verification(user)
        return user

    async def login(self, data: LoginRequest, device_info: DeviceInfo) -> TokenResponse:
        user = await self._user_repository.get_by_email(data.email)
        if user is None or not user.is_active:
            raise InvalidCredentialsException()
        if user.is_locked():
            raise AccountLockedException()
        if not verify_password(data.password, user.password_hash):
            await self._handle_failed_login(user)
            raise InvalidCredentialsException()

        user.record_successful_login()
        await self._user_repository.update(user, {})
        await self._clear_login_attempts(user.email)

        refresh_session = await self._create_refresh_session(user, device_info, data.remember_me)
        access_token = self._create_access_token(user, refresh_session)
        refresh_token = self._create_refresh_token(refresh_session, data.remember_me)
        await self._store_refresh_session(refresh_session)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.jwt_access_token_expire_minutes * 60,
        )

    async def refresh(self, token: str, device_info: DeviceInfo) -> TokenResponse:
        payload = decode_token(token)
        if payload.get("type") != "refresh":
            raise InvalidOrExpiredTokenException()

        token_hash = sha256(token.encode()).hexdigest()
        session = await self._refresh_repository.get_by_token_hash(token_hash)
        if session is None or not session.is_active():
            raise SessionExpiredException()

        await self._refresh_repository.revoke(session)
        await self._delete_cached_session(session)

        user = session.user
        refresh_session = await self._create_refresh_session(user, device_info, False)
        access_token = self._create_access_token(user, refresh_session)
        refresh_token = self._create_refresh_token(refresh_session, False)
        await self._store_refresh_session(refresh_session)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.jwt_access_token_expire_minutes * 60,
        )

    async def logout(self, token: str, access_token: str | None = None) -> None:
        try:
            payload = decode_token(token)
        except Exception as exc:
            raise InvalidOrExpiredTokenException() from exc

        if payload.get("type") != "refresh":
            raise InvalidOrExpiredTokenException()

        token_hash = sha256(token.encode()).hexdigest()
        session = await self._refresh_repository.get_by_token_hash(token_hash)
        if session is not None:
            await self._refresh_repository.revoke(session)
            await self._delete_cached_session(session)

        if access_token:
            await self._blacklist_access_token(access_token)

    async def change_password(self, user: User, data: ChangePasswordRequest) -> None:
        if not verify_password(data.current_password, user.password_hash):
            raise InvalidCredentialsException()
        await self._user_repository.update(
            user, {"password_hash": hash_password(data.new_password)}
        )
        await self.revoke_all_sessions(user.id)

    async def forgot_password(self, email: str) -> None:
        user = await self._user_repository.get_by_email(email)
        if user is not None:
            token = token_urlsafe(32)
            redis = RedisManager.get()
            await redis.setex(
                f"password_reset:{token}",
                3600,
                str(user.id),
            )

    async def reset_password(self, data: ResetPasswordRequest) -> User:
        redis = RedisManager.get()
        user_id = await redis.get(f"password_reset:{data.token}")
        if not user_id:
            raise PasswordResetTokenInvalidException()
        await redis.delete(f"password_reset:{data.token}")

        user = await self._user_repository.get(UUID(user_id))
        if user is None:
            raise PasswordResetTokenInvalidException()

        await self._user_repository.update(
            user, {"password_hash": hash_password(data.new_password)}
        )
        await self.revoke_all_sessions(user.id)
        return user

    async def verify_email(self, data: VerifyEmailRequest) -> User:
        redis = RedisManager.get()
        user_id = await redis.get(f"email_verify:{data.token}")
        if not user_id:
            raise EmailVerificationTokenInvalidException()
        await redis.delete(f"email_verify:{data.token}")

        user = await self._user_repository.get(UUID(user_id))
        if user is None:
            raise EmailVerificationTokenInvalidException()

        return await self._user_service.verify_email(user)

    async def revoke_all_sessions(self, user_id: UUID) -> None:
        await self._refresh_repository.revoke_all_for_user(user_id)
        redis = RedisManager.get()
        session_hashes = await redis.smembers(f"user_sessions:{user_id}")  # type: ignore[misc]
        if session_hashes:
            keys = [f"refresh:{h}" for h in session_hashes]
            await redis.delete(*keys)
            await redis.delete(f"user_sessions:{user_id}")

    async def get_user_sessions(self, user_id: UUID) -> list[RefreshSession]:
        return await self._refresh_repository.list_by_user(user_id)

    async def _create_refresh_session(
        self, user: User, device_info: DeviceInfo, remember_me: bool
    ) -> RefreshSession:
        days = (
            settings.jwt_refresh_token_expire_days * 2
            if remember_me
            else settings.jwt_refresh_token_expire_days
        )
        expires_at = datetime.now(UTC) + timedelta(days=days)
        session = RefreshSession(
            user_id=user.id,
            device_fingerprint=device_info.fingerprint,
            user_agent=device_info.user_agent,
            ip_address=device_info.ip_address,
            expires_at=expires_at,
        )
        return await self._refresh_repository.create(session)

    def _create_access_token(self, user: User, session: RefreshSession) -> str:
        return create_access_token(
            user.id,
            extra_claims={
                "email": user.email,
                "is_verified": user.is_verified,
                "session_id": str(session.id),
                "jti": str(uuid4()),
            },
        )

    def _create_refresh_token(self, session: RefreshSession, remember_me: bool) -> str:
        token = create_refresh_token(
            session.user_id,
            remember_me=remember_me,
            extra_claims={"session_id": str(session.id)},
        )
        session.token_hash = sha256(token.encode()).hexdigest()
        return token

    async def _store_refresh_session(self, session: RefreshSession) -> None:
        await self._refresh_repository.update(session, {"token_hash": session.token_hash})
        redis = RedisManager.get()
        ttl = int((session.expires_at - datetime.now(UTC)).total_seconds())
        if ttl > 0:
            await redis.setex(f"refresh:{session.token_hash}", ttl, "1")
        await redis.sadd(  # type: ignore[misc]
            f"user_sessions:{session.user_id}", session.token_hash
        )

    async def _delete_cached_session(self, session: RefreshSession) -> None:
        redis = RedisManager.get()
        await redis.delete(f"refresh:{session.token_hash}")
        await redis.srem(  # type: ignore[misc]
            f"user_sessions:{session.user_id}", session.token_hash
        )

    async def _handle_failed_login(self, user: User) -> None:
        user.record_failed_login()
        redis = RedisManager.get()
        key = f"login_attempts:{user.email}"
        attempts = await redis.incr(key)
        await redis.expire(key, settings.login_lockout_minutes * 60)

        if attempts >= settings.max_login_attempts:
            user.lock(settings.login_lockout_minutes)
        await self._user_repository.update(user, {})

    async def _clear_login_attempts(self, email: str) -> None:
        redis = RedisManager.get()
        await redis.delete(f"login_attempts:{email}")

    async def _blacklist_access_token(self, token: str) -> None:
        try:
            payload = decode_token(token)
        except Exception:
            return

        jti = payload.get("jti")
        exp = payload.get("exp")
        if jti is None or exp is None:
            return

        ttl = int(exp - datetime.now(UTC).timestamp())
        if ttl > 0:
            redis = RedisManager.get()
            await redis.setex(f"blacklist:{jti}", ttl, "1")

    async def _send_email_verification(self, user: User) -> str:
        token = token_urlsafe(32)
        redis = RedisManager.get()
        await redis.setex(f"email_verify:{token}", 24 * 3600, str(user.id))
        return token
