from typing import Any
from uuid import UUID

from fastapi import Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user
from app.core.database import get_db
from app.core.exceptions import AuthorizationException
from app.organizations.repository import OrganizationRepository
from app.permissions.dependencies import (
    get_authorization_service,
    get_role_repository,
    get_user_role_repository,
)
from app.permissions.repository import RoleRepository, UserRoleRepository
from app.permissions.service import AuthorizationService
from app.teams.exceptions import TeamNotFoundException
from app.teams.models import Team
from app.teams.repository import TeamRepository
from app.teams.service import TeamService
from app.users.dependencies import get_user_repository
from app.users.models import User
from app.users.repository import UserRepository


def get_team_repository(
    session: AsyncSession = Depends(get_db),
) -> TeamRepository:
    return TeamRepository(session)


def get_organization_repository(
    session: AsyncSession = Depends(get_db),
) -> OrganizationRepository:
    return OrganizationRepository(session)


def get_team_service(
    team_repository: TeamRepository = Depends(get_team_repository),
    organization_repository: OrganizationRepository = Depends(get_organization_repository),
    role_repository: RoleRepository = Depends(get_role_repository),
    user_role_repository: UserRoleRepository = Depends(get_user_role_repository),
    user_repository: UserRepository = Depends(get_user_repository),
) -> TeamService:
    return TeamService(
        team_repository,
        organization_repository,
        role_repository,
        user_role_repository,
        user_repository,
    )


async def get_team(
    team_id: UUID = Path(...),
    repository: TeamRepository = Depends(get_team_repository),
) -> Team:
    team = await repository.get_active_by_id(team_id)
    if team is None:
        raise TeamNotFoundException()
    return team


def require_team_permission(permission: str) -> Any:
    async def _check_permission(
        team_id: UUID,
        current_user: User = Depends(get_current_active_user),
        auth_service: AuthorizationService = Depends(get_authorization_service),
    ) -> User:
        if not await auth_service.has_permission(current_user.id, permission, team_id=team_id):
            raise AuthorizationException()
        return current_user

    return _check_permission
