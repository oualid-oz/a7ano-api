from typing import Any
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user
from app.core.database import get_db
from app.core.exceptions import AuthorizationException
from app.permissions.repository import (
    PermissionRepository,
    RoleRepository,
    UserRoleRepository,
)
from app.permissions.service import (
    AuthorizationService,
    PermissionService,
    RoleService,
)
from app.users.models import User


def get_permission_repository(
    session: AsyncSession = Depends(get_db),
) -> PermissionRepository:
    return PermissionRepository(session)


def get_role_repository(
    session: AsyncSession = Depends(get_db),
) -> RoleRepository:
    return RoleRepository(session)


def get_user_role_repository(
    session: AsyncSession = Depends(get_db),
) -> UserRoleRepository:
    return UserRoleRepository(session)


def get_permission_service(
    repository: PermissionRepository = Depends(get_permission_repository),
) -> PermissionService:
    return PermissionService(repository)


def get_role_service(
    permission_repository: PermissionRepository = Depends(get_permission_repository),
    role_repository: RoleRepository = Depends(get_role_repository),
    user_role_repository: UserRoleRepository = Depends(get_user_role_repository),
) -> RoleService:
    return RoleService(permission_repository, role_repository, user_role_repository)


def get_authorization_service(
    permission_repository: PermissionRepository = Depends(get_permission_repository),
    role_repository: RoleRepository = Depends(get_role_repository),
    user_role_repository: UserRoleRepository = Depends(get_user_role_repository),
) -> AuthorizationService:
    return AuthorizationService(permission_repository, role_repository, user_role_repository)


def require_permission(
    permission: str,
    organization_id: UUID | None = None,
    team_id: UUID | None = None,
) -> Any:
    async def _check_permission(
        user: User = Depends(get_current_active_user),
        service: AuthorizationService = Depends(get_authorization_service),
    ) -> User:
        if not await service.has_permission(user.id, permission, organization_id, team_id):
            raise AuthorizationException()
        return user

    return _check_permission


def require_role(
    role_name: str,
    organization_id: UUID | None = None,
    team_id: UUID | None = None,
) -> Any:
    async def _check_role(
        user: User = Depends(get_current_active_user),
        service: AuthorizationService = Depends(get_authorization_service),
    ) -> User:
        if not await service.has_role(user.id, role_name, organization_id, team_id):
            raise AuthorizationException()
        return user

    return _check_role
