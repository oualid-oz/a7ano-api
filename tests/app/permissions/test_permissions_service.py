"""Unit tests for PermissionService, RoleService, and AuthorizationService."""
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.core.exceptions import DuplicateValueException
from app.permissions.exceptions import PermissionNotFoundException, RoleNotFoundException
from app.permissions.schemas import PermissionCreate, RoleCreate
from app.permissions.service import AuthorizationService, PermissionService, RoleService

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_permission(name="project:read", resource="project", action="read"):
    perm = MagicMock()
    perm.id = uuid4()
    perm.name = name
    perm.resource = resource
    perm.action = action
    perm.description = None
    return perm


def _make_role(role_id=None, name="member", permissions=None):
    role = MagicMock()
    role.id = role_id or uuid4()
    role.name = name
    role.description = f"Role: {name}"
    role.is_system = False
    role.permissions = permissions or []
    return role


def _make_user_role(user_id=None, role=None):
    ur = MagicMock()
    ur.id = uuid4()
    ur.user_id = user_id or uuid4()
    ur.role = role or _make_role()
    return ur


# ── TestPermissionService ─────────────────────────────────────────────────────


@pytest.mark.anyio
class TestPermissionService:
    def _make_service(self, repo=None) -> PermissionService:
        return PermissionService(repository=repo or AsyncMock())

    async def test_create_permission_success(self):
        perm = _make_permission(name="project:export", resource="project", action="export")
        repo = AsyncMock()
        repo.get_by_name.return_value = None
        repo.create.return_value = perm

        service = self._make_service(repo=repo)
        data = PermissionCreate(name="project:export", resource="project", action="export")
        result = await service.create(data)

        assert result is perm
        repo.create.assert_awaited_once()

    async def test_create_permission_duplicate(self):
        existing = _make_permission()
        repo = AsyncMock()
        repo.get_by_name.return_value = existing

        service = self._make_service(repo=repo)
        data = PermissionCreate(name="project:read", resource="project", action="read")

        with pytest.raises(DuplicateValueException):
            await service.create(data)

    async def test_get_by_name_found(self):
        perm = _make_permission()
        repo = AsyncMock()
        repo.get_by_name.return_value = perm

        service = self._make_service(repo=repo)
        result = await service.get_by_name("project:read")

        assert result is perm

    async def test_get_by_name_not_found(self):
        repo = AsyncMock()
        repo.get_by_name.return_value = None

        service = self._make_service(repo=repo)
        with pytest.raises(PermissionNotFoundException):
            await service.get_by_name("nonexistent:perm")


# ── TestRoleService ───────────────────────────────────────────────────────────


@pytest.mark.anyio
class TestRoleService:
    def _make_service(
        self,
        perm_repo=None,
        role_repo=None,
        user_role_repo=None,
    ) -> RoleService:
        return RoleService(
            permission_repository=perm_repo or AsyncMock(),
            role_repository=role_repo or AsyncMock(),
            user_role_repository=user_role_repo or AsyncMock(),
        )

    async def test_create_role_success(self):
        perm = _make_permission(name="project:read")
        role = _make_role(name="reviewer", permissions=[perm])

        perm_repo = AsyncMock()
        perm_repo.get_by_name.return_value = perm

        role_repo = AsyncMock()
        role_repo.get_by_name.return_value = None
        role_repo.create.return_value = role

        service = self._make_service(perm_repo=perm_repo, role_repo=role_repo)
        data = RoleCreate(name="reviewer", permission_names=["project:read"])
        result = await service.create(data)

        assert result is role
        role_repo.create.assert_awaited_once()
        created_role_arg = role_repo.create.call_args[0][0]
        assert perm in created_role_arg.permissions

    async def test_create_role_duplicate_name(self):
        existing = _make_role(name="member")
        role_repo = AsyncMock()
        role_repo.get_by_name.return_value = existing

        service = self._make_service(role_repo=role_repo)
        data = RoleCreate(name="member")

        with pytest.raises(DuplicateValueException):
            await service.create(data)

    async def test_get_role_found(self):
        role = _make_role()
        role_repo = AsyncMock()
        role_repo.get_with_permissions.return_value = role

        service = self._make_service(role_repo=role_repo)
        result = await service.get(role.id)

        assert result is role
        role_repo.get_with_permissions.assert_awaited_once_with(role.id)

    async def test_get_role_not_found(self):
        role_repo = AsyncMock()
        role_repo.get_with_permissions.return_value = None

        service = self._make_service(role_repo=role_repo)
        with pytest.raises(RoleNotFoundException):
            await service.get(uuid4())


# ── TestAuthorizationService ──────────────────────────────────────────────────


@pytest.mark.anyio
class TestAuthorizationService:
    def _make_service(
        self,
        perm_repo=None,
        role_repo=None,
        user_role_repo=None,
    ) -> AuthorizationService:
        return AuthorizationService(
            permission_repository=perm_repo or AsyncMock(),
            role_repository=role_repo or AsyncMock(),
            user_role_repository=user_role_repo or AsyncMock(),
        )

    async def test_has_permission_exact_match(self):
        user_id = uuid4()
        perm = _make_permission(name="project:read")
        role = _make_role(name="member", permissions=[perm])
        assignment = _make_user_role(user_id=user_id, role=role)

        user_role_repo = AsyncMock()
        user_role_repo.list_by_user_and_scope.return_value = [assignment]

        service = self._make_service(user_role_repo=user_role_repo)
        result = await service.has_permission(user_id, "project:read")

        assert result is True

    async def test_has_permission_wildcard(self):
        """project:* in granted permissions covers project:delete."""
        user_id = uuid4()
        perm = _make_permission(name="project:*", resource="project", action="*")
        role = _make_role(name="project_admin", permissions=[perm])
        assignment = _make_user_role(user_id=user_id, role=role)

        user_role_repo = AsyncMock()
        user_role_repo.list_by_user_and_scope.return_value = [assignment]

        service = self._make_service(user_role_repo=user_role_repo)
        result = await service.has_permission(user_id, "project:delete")

        assert result is True

    async def test_has_permission_missing(self):
        user_id = uuid4()
        perm = _make_permission(name="team:read", resource="team", action="read")
        role = _make_role(name="viewer", permissions=[perm])
        assignment = _make_user_role(user_id=user_id, role=role)

        user_role_repo = AsyncMock()
        user_role_repo.list_by_user_and_scope.return_value = [assignment]

        service = self._make_service(user_role_repo=user_role_repo)
        result = await service.has_permission(user_id, "project:read")

        assert result is False

    async def test_has_role_found(self):
        user_id = uuid4()
        role = _make_role(name="member")
        assignment = _make_user_role(user_id=user_id, role=role)

        user_role_repo = AsyncMock()
        user_role_repo.list_by_user_and_scope.return_value = [assignment]

        service = self._make_service(user_role_repo=user_role_repo)
        result = await service.has_role(user_id, "member")

        assert result is True

    async def test_has_role_not_found(self):
        user_id = uuid4()
        role = _make_role(name="guest")
        assignment = _make_user_role(user_id=user_id, role=role)

        user_role_repo = AsyncMock()
        user_role_repo.list_by_user_and_scope.return_value = [assignment]

        service = self._make_service(user_role_repo=user_role_repo)
        result = await service.has_role(user_id, "admin")

        assert result is False

    async def test_seed_defaults_creates_permissions_and_roles(self):
        perm_repo = AsyncMock()
        perm_repo.get_by_name.return_value = None

        created_perms: list = []

        async def _create_perm(p):
            created_perms.append(p)
            return p

        perm_repo.create.side_effect = _create_perm

        role_repo = AsyncMock()
        role_repo.get_by_name.return_value = None

        async def _create_role(r):
            return r

        role_repo.create.side_effect = _create_role

        service = self._make_service(perm_repo=perm_repo, role_repo=role_repo)
        await service.seed_defaults()

        assert perm_repo.create.await_count > 0
        assert role_repo.create.await_count > 0

    async def test_seed_defaults_skips_existing_permissions(self):
        existing_perm = _make_permission()
        perm_repo = AsyncMock()
        perm_repo.get_by_name.return_value = existing_perm  # already exists

        role_repo = AsyncMock()
        role_repo.get_by_name.return_value = None

        async def _create_role(r):
            return r

        role_repo.create.side_effect = _create_role

        service = self._make_service(perm_repo=perm_repo, role_repo=role_repo)
        await service.seed_defaults()

        # Permissions already exist → create not called for them
        perm_repo.create.assert_not_awaited()
