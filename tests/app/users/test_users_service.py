"""Unit tests for UserService — no database required."""
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.core.exceptions import ResourceNotFoundException
from app.users.exceptions import EmailAlreadyExistsException, UserNotFoundException
from app.users.schemas import UserCreate, UserUpdate
from app.users.service import UserService

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_user(user_id=None, email="user@example.com"):
    user = MagicMock()
    user.id = user_id or uuid4()
    user.email = email
    user.full_name = "Test User"
    user.avatar_url = None
    user.is_active = True
    user.is_verified = False
    user.deleted_at = None
    user.password_hash = "hashed"
    return user


# ── TestUserService ───────────────────────────────────────────────────────────


@pytest.mark.anyio
class TestUserService:
    def _make_service(self, repo=None) -> UserService:
        return UserService(repository=repo or AsyncMock())

    async def test_create_user_success(self):
        repo = AsyncMock()
        repo.get_by_email.return_value = None
        created = _make_user()
        repo.create.return_value = created

        service = self._make_service(repo=repo)
        data = UserCreate(
            email="new@example.com", password="SecureP@ssw0rd!", full_name="New User"
        )
        result = await service.create(data)

        assert result is created
        repo.create.assert_awaited_once()
        # Password hashed — not stored as plaintext
        created_user_arg = repo.create.call_args[0][0]
        assert created_user_arg.password_hash != "SecureP@ssw0rd!"

    async def test_create_user_email_exists(self):
        repo = AsyncMock()
        repo.get_by_email.return_value = _make_user()

        service = self._make_service(repo=repo)
        data = UserCreate(
            email="existing@example.com", password="SecureP@ssw0rd!", full_name="Existing User"
        )
        with pytest.raises(EmailAlreadyExistsException):
            await service.create(data)

    async def test_get_user_found(self):
        user = _make_user()
        repo = AsyncMock()
        repo.get_or_404.return_value = user

        service = self._make_service(repo=repo)
        result = await service.get_by_id(user.id)

        assert result is user
        repo.get_or_404.assert_awaited_once_with(user.id)

    async def test_get_user_not_found(self):
        repo = AsyncMock()
        repo.get_or_404.side_effect = ResourceNotFoundException()

        service = self._make_service(repo=repo)
        with pytest.raises(ResourceNotFoundException):
            await service.get_by_id(uuid4())

    async def test_get_by_email_found(self):
        user = _make_user()
        repo = AsyncMock()
        repo.get_by_email.return_value = user

        service = self._make_service(repo=repo)
        result = await service.get_by_email(user.email)

        assert result is user

    async def test_get_by_email_not_found(self):
        repo = AsyncMock()
        repo.get_by_email.return_value = None

        service = self._make_service(repo=repo)
        with pytest.raises(UserNotFoundException):
            await service.get_by_email("missing@example.com")

    async def test_update_profile_success(self):
        user = _make_user()
        updated = _make_user(user_id=user.id)
        updated.full_name = "Updated Name"
        updated.avatar_url = "https://example.com/avatar.png"
        repo = AsyncMock()
        repo.update.return_value = updated

        service = self._make_service(repo=repo)
        data = UserUpdate(
            full_name="Updated Name", avatar_url="https://example.com/avatar.png"
        )
        result = await service.update_profile(user, data)

        assert result is updated
        repo.update.assert_awaited_once()
        update_dict = repo.update.call_args[0][1]
        assert update_dict.get("full_name") == "Updated Name"
        assert update_dict.get("avatar_url") == "https://example.com/avatar.png"

    async def test_update_profile_excludes_unset_fields(self):
        user = _make_user()
        repo = AsyncMock()
        repo.update.return_value = user

        service = self._make_service(repo=repo)
        # Only full_name set, avatar_url omitted
        data = UserUpdate(full_name="Only Name")
        await service.update_profile(user, data)

        update_dict = repo.update.call_args[0][1]
        assert "full_name" in update_dict
        assert "avatar_url" not in update_dict

    async def test_verify_email_unverified(self):
        user = _make_user()
        user.is_verified = False
        verified = _make_user(user_id=user.id)
        verified.is_verified = True
        repo = AsyncMock()
        repo.update.return_value = verified

        service = self._make_service(repo=repo)
        result = await service.verify_email(user)

        assert result is verified
        repo.update.assert_awaited_once_with(user, {"is_verified": True})

    async def test_verify_email_already_verified_skips_update(self):
        user = _make_user()
        user.is_verified = True
        repo = AsyncMock()

        service = self._make_service(repo=repo)
        result = await service.verify_email(user)

        assert result is user
        repo.update.assert_not_awaited()
