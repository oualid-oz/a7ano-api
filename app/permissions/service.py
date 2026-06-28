from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.schemas import PaginationMeta, PaginationParams
from app.core.exceptions import DuplicateValueException, ResourceNotFoundException
from app.permissions.constants import DEFAULT_PERMISSIONS, DEFAULT_ROLES
from app.permissions.exceptions import (
    PermissionNotFoundException,
    RoleAlreadyAssignedException,
    RoleNotFoundException,
)
from app.permissions.models import Permission, Role, UserRole
from app.permissions.repository import (
    PermissionRepository,
    RoleRepository,
    UserRoleRepository,
)
from app.permissions.schemas import (
    PermissionCreate,
    RoleCreate,
    RoleUpdate,
    UserRoleAssign,
    UserRoleRemove,
)


class PermissionService:
    def __init__(self, repository: PermissionRepository) -> None:
        self._repository = repository

    async def create(self, data: PermissionCreate) -> Permission:
        existing = await self._repository.get_by_name(data.name)
        if existing is not None:
            raise DuplicateValueException("Permission name already exists.")
        permission = Permission(
            name=data.name,
            resource=data.resource,
            action=data.action,
            description=data.description,
        )
        return await self._repository.create(permission)

    async def get_by_name(self, name: str) -> Permission:
        permission = await self._repository.get_by_name(name)
        if permission is None:
            raise PermissionNotFoundException()
        return permission

    async def list_permissions(
        self, pagination: PaginationParams
    ) -> tuple[list[Permission], PaginationMeta]:
        return await self._repository.list(pagination)


class RoleService:
    def __init__(
        self,
        permission_repository: PermissionRepository,
        role_repository: RoleRepository,
        user_role_repository: UserRoleRepository,
    ) -> None:
        self._permission_repository = permission_repository
        self._role_repository = role_repository
        self._user_role_repository = user_role_repository

    async def get(self, role_id: UUID) -> Role:
        role = await self._role_repository.get_with_permissions(role_id)
        if role is None:
            raise RoleNotFoundException()
        return role

    async def list_roles(self, pagination: PaginationParams) -> tuple[list[Role], PaginationMeta]:
        return await self._role_repository.list(pagination)

    async def create(self, data: RoleCreate) -> Role:
        existing = await self._role_repository.get_by_name(data.name)
        if existing is not None:
            raise DuplicateValueException("Role name already exists.")
        permissions = await self._resolve_permissions(data.permission_names)
        role = Role(
            name=data.name,
            description=data.description,
            is_system=False,
            permissions=permissions,
        )
        return await self._role_repository.create(role)

    async def update(self, role_id: UUID, data: RoleUpdate) -> Role:
        role = await self._role_repository.get_with_permissions(role_id)
        if role is None:
            raise RoleNotFoundException()

        update_fields = {}
        if data.description is not None:
            update_fields["description"] = data.description
        if update_fields:
            role = await self._role_repository.update(role, update_fields)

        if data.permission_names is not None:
            role.permissions = await self._resolve_permissions(data.permission_names)
            await self._role_repository.session.flush()
            await self._role_repository.session.refresh(role)

        return role

    async def assign_role(self, data: UserRoleAssign) -> UserRole:
        existing = await self._user_role_repository.get_assignment(
            data.user_id,
            data.role_id,
            data.organization_id,
            data.team_id,
        )
        if existing is not None:
            raise RoleAlreadyAssignedException()

        role = await self._role_repository.get_or_404(data.role_id)
        assignment = UserRole(
            user_id=data.user_id,
            role_id=role.id,
            organization_id=data.organization_id,
            team_id=data.team_id,
        )
        return await self._user_role_repository.create(assignment)

    async def remove_role(self, data: UserRoleRemove) -> None:
        assignment = await self._user_role_repository.get_assignment(
            data.user_id,
            data.role_id,
            data.organization_id,
            data.team_id,
        )
        if assignment is None:
            raise ResourceNotFoundException("Role assignment not found.")
        await self._user_role_repository.delete_soft(assignment)

    async def list_user_roles(self, user_id: UUID) -> list[UserRole]:
        return await self._user_role_repository.list_by_user(user_id)

    async def _resolve_permissions(self, names: list[str]) -> list[Permission]:
        permissions: list[Permission] = []
        seen: set[str] = set()
        for name in names:
            if name.endswith(":*"):
                resource = name[:-2]
                perms = await self._permission_repository.get_by_resource(resource)
                for p in perms:
                    if p.name not in seen:
                        seen.add(p.name)
                        permissions.append(p)
            else:
                if name in seen:
                    continue
                seen.add(name)
                permission = await self._permission_repository.get_by_name(name)
                if permission is None:
                    raise PermissionNotFoundException()
                permissions.append(permission)
        return permissions


class AuthorizationService:
    def __init__(
        self,
        permission_repository: PermissionRepository,
        role_repository: RoleRepository,
        user_role_repository: UserRoleRepository,
    ) -> None:
        self._permission_repository = permission_repository
        self._role_repository = role_repository
        self._user_role_repository = user_role_repository

    async def has_permission(
        self,
        user_id: UUID,
        permission: str,
        organization_id: UUID | None = None,
        team_id: UUID | None = None,
    ) -> bool:
        user_permissions = await self.get_user_permissions(user_id, organization_id, team_id)
        return self._permission_matches(permission, user_permissions)

    async def get_user_permissions(
        self,
        user_id: UUID,
        organization_id: UUID | None = None,
        team_id: UUID | None = None,
    ) -> set[str]:
        assignments = await self._user_role_repository.list_by_user_and_scope(
            user_id, organization_id, team_id
        )
        permissions: set[str] = set()
        for assignment in assignments:
            for perm in assignment.role.permissions:
                permissions.add(perm.name)
        return permissions

    async def has_role(
        self,
        user_id: UUID,
        role_name: str,
        organization_id: UUID | None = None,
        team_id: UUID | None = None,
    ) -> bool:
        assignments = await self._user_role_repository.list_by_user_and_scope(
            user_id, organization_id, team_id
        )
        return any(a.role.name == role_name for a in assignments)

    async def seed_defaults(self) -> None:
        permission_map: dict[str, Permission] = {}
        for name, resource, action in DEFAULT_PERMISSIONS:
            existing = await self._permission_repository.get_by_name(name)
            if existing is None:
                perm = Permission(name=name, resource=resource, action=action)
                perm = await self._permission_repository.create(perm)
            else:
                perm = existing
            permission_map[name] = perm

        for role_name, role_data in DEFAULT_ROLES.items():
            role = await self._role_repository.get_by_name(role_name)
            if role is None:
                permissions = self._resolve_default_permissions(
                    role_data["permissions"], permission_map
                )
                role = Role(
                    name=role_name,
                    description=role_data["description"],
                    is_system=True,
                    permissions=permissions,
                )
                await self._role_repository.create(role)

    def _permission_matches(self, required: str, granted: set[str]) -> bool:
        if required in granted:
            return True
        if "*:*" in granted:
            return True
        parts = required.split(":")
        if len(parts) == 2:
            wildcard = f"{parts[0]}:*"
            if wildcard in granted:
                return True
        return False

    def _resolve_default_permissions(
        self, names: list[str], permission_map: dict[str, Permission]
    ) -> list[Permission]:
        permissions: list[Permission] = []
        seen: set[str] = set()
        for name in names:
            if name.endswith(":*"):
                resource = name[:-2]
                for perm_name, perm in permission_map.items():
                    if perm.resource == resource and perm_name not in seen:
                        seen.add(perm_name)
                        permissions.append(perm)
            elif name not in seen:
                seen.add(name)
                if name in permission_map:
                    permissions.append(permission_map[name])
        return permissions


async def seed_permissions_and_roles(session: AsyncSession) -> None:
    permission_repo = PermissionRepository(session)
    role_repo = RoleRepository(session)
    user_role_repo = UserRoleRepository(session)
    service = AuthorizationService(permission_repo, role_repo, user_role_repo)
    await service.seed_defaults()
