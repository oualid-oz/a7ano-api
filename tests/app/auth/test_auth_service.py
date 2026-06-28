"""Unit tests for AuthService — no database required."""
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.auth.exceptions import (
    AccountLockedException,
    InvalidCredentialsException,
)
from app.auth.schemas import ChangePasswordRequest, DeviceInfo, LoginRequest, RegisterRequest
from app.auth.service import AuthService
from app.core.security import hash_password

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_device_info() -> DeviceInfo:
    return DeviceInfo(user_agent="pytest/1.0", ip_address="127.0.0.1", fingerprint=None)


def _make_user(user_id=None, email="user@example.com", password="SecureP@ssw0rd!"):
    user = MagicMock()
    user.id = user_id or uuid4()
    user.email = email
    user.full_name = "Test User"
    user.password_hash = hash_password(password)
    user.is_active = True
    user.is_verified = False
    user.deleted_at = None
    user.is_locked.return_value = False
    return user


def _make_refresh_session(user_id=None):
    from datetime import UTC, datetime, timedelta

    session = MagicMock()
    session.id = uuid4()
    session.user_id = user_id or uuid4()
    session.token_hash = "some-hash"
    session.expires_at = datetime.now(UTC) + timedelta(days=7)
    session.is_active.return_value = True
    session.user = MagicMock()
    session.user.id = session.user_id
    session.user.email = "user@example.com"
    session.user.is_verified = False
    return session


# ── TestAuthService ───────────────────────────────────────────────────────────


@pytest.mark.anyio
class TestAuthService:
    def _make_service(
        self,
        user_repo=None,
        user_service=None,
        refresh_repo=None,
    ) -> AuthService:
        return AuthService(
            user_repository=user_repo or AsyncMock(),
            user_service=user_service or AsyncMock(),
            refresh_repository=refresh_repo or AsyncMock(),
        )

    async def test_register_success(self):
        user = _make_user()
        user_service = AsyncMock()
        user_service.create.return_value = user

        with patch("app.auth.service.RedisManager") as mock_rm:
            mock_redis = AsyncMock()
            mock_rm.get.return_value = mock_redis

            service = self._make_service(user_service=user_service)
            data = RegisterRequest(
                email="user@example.com",
                password="SecureP@ssw0rd!",
                full_name="Test User",
            )
            result = await service.register(data, _make_device_info())

        assert result is user
        user_service.create.assert_awaited_once()
        mock_redis.setex.assert_awaited_once()

    async def test_login_success(self):
        password = "SecureP@ssw0rd!"
        user = _make_user(password=password)
        refresh_session = _make_refresh_session(user_id=user.id)

        user_repo = AsyncMock()
        user_repo.get_by_email.return_value = user
        user_repo.update.return_value = user

        refresh_repo = AsyncMock()
        refresh_repo.create.return_value = refresh_session
        refresh_repo.update.return_value = refresh_session

        with patch("app.auth.service.RedisManager") as mock_rm:
            mock_redis = AsyncMock()
            mock_rm.get.return_value = mock_redis

            service = self._make_service(user_repo=user_repo, refresh_repo=refresh_repo)
            data = LoginRequest(email=user.email, password=password, remember_me=False)
            result = await service.login(data, _make_device_info())

        assert result.access_token
        assert result.refresh_token
        assert result.token_type == "bearer"
        assert result.expires_in > 0

    async def test_login_user_not_found(self):
        user_repo = AsyncMock()
        user_repo.get_by_email.return_value = None

        service = self._make_service(user_repo=user_repo)
        data = LoginRequest(email="nobody@example.com", password="anything")

        with pytest.raises(InvalidCredentialsException):
            await service.login(data, _make_device_info())

    async def test_login_wrong_password(self):
        user = _make_user(password="CorrectP@ssw0rd!")
        user_repo = AsyncMock()
        user_repo.get_by_email.return_value = user
        user_repo.update.return_value = user

        with patch("app.auth.service.RedisManager") as mock_rm:
            mock_redis = AsyncMock()
            mock_redis.incr.return_value = 1
            mock_rm.get.return_value = mock_redis

            service = self._make_service(user_repo=user_repo)
            data = LoginRequest(email=user.email, password="WrongP@ssw0rd!")

            with pytest.raises(InvalidCredentialsException):
                await service.login(data, _make_device_info())

    async def test_login_locked_account(self):
        user = _make_user()
        user.is_locked.return_value = True
        user_repo = AsyncMock()
        user_repo.get_by_email.return_value = user

        service = self._make_service(user_repo=user_repo)
        data = LoginRequest(email=user.email, password="anything")

        with pytest.raises(AccountLockedException):
            await service.login(data, _make_device_info())

    async def test_change_password_success(self):
        password = "OldP@ssw0rd!"
        user = _make_user(password=password)
        user_repo = AsyncMock()
        user_repo.update.return_value = user

        refresh_repo = AsyncMock()
        refresh_repo.revoke_all_for_user.return_value = None

        with patch("app.auth.service.RedisManager") as mock_rm:
            mock_redis = AsyncMock()
            mock_redis.smembers.return_value = set()
            mock_rm.get.return_value = mock_redis

            service = self._make_service(user_repo=user_repo, refresh_repo=refresh_repo)
            data = ChangePasswordRequest(
                current_password=password, new_password="NewP@ssw0rd!"
            )
            await service.change_password(user, data)

        user_repo.update.assert_awaited_once()
        update_args = user_repo.update.call_args[0]
        assert "password_hash" in update_args[1]
        assert update_args[1]["password_hash"] != user.password_hash

    async def test_change_password_wrong_current(self):
        user = _make_user(password="CorrectP@ssw0rd!")
        user_repo = AsyncMock()

        service = self._make_service(user_repo=user_repo)
        data = ChangePasswordRequest(
            current_password="WrongP@ssw0rd!", new_password="NewP@ssw0rd!"
        )
        with pytest.raises(InvalidCredentialsException):
            await service.change_password(user, data)

    async def test_forgot_password_existing_user(self):
        user = _make_user()
        user_repo = AsyncMock()
        user_repo.get_by_email.return_value = user

        with patch("app.auth.service.RedisManager") as mock_rm:
            mock_redis = AsyncMock()
            mock_rm.get.return_value = mock_redis

            service = self._make_service(user_repo=user_repo)
            await service.forgot_password(user.email)

        mock_redis.setex.assert_awaited_once()
        key_arg = mock_redis.setex.call_args[0][0]
        assert key_arg.startswith("password_reset:")

    async def test_forgot_password_nonexistent_user_silent(self):
        """Silently succeeds when the email is not registered."""
        user_repo = AsyncMock()
        user_repo.get_by_email.return_value = None

        with patch("app.auth.service.RedisManager") as mock_rm:
            mock_redis = AsyncMock()
            mock_rm.get.return_value = mock_redis

            service = self._make_service(user_repo=user_repo)
            await service.forgot_password("nonexistent@example.com")

        mock_redis.setex.assert_not_awaited()
