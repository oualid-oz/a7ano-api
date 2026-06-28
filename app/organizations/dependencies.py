from typing import Any
from uuid import UUID

from fastapi import Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user
from app.core.database import get_db
from app.core.exceptions import AuthorizationException
from app.organizations.exceptions import OrganizationNotFoundException
from app.organizations.models import Organization
from app.organizations.repository import (
    InvitationRepository,
    OrganizationRepository,
)
from app.organizations.service import OrganizationService
from app.permissions.dependencies import (
    get_authorization_service,
    get_role_repository,
    get_user_role_repository,
)
from app.permissions.repository import RoleRepository, UserRoleRepository
from app.permissions.service import AuthorizationService
from app.users.dependencies import get_user_repository
from app.users.models import User
from app.users.repository import UserRepository


def get_organization_repository(
    session: AsyncSession = Depends(get_db),
) -> OrganizationRepository:
    return OrganizationRepository(session)


def get_invitation_repository(
    session: AsyncSession = Depends(get_db),
) -> InvitationRepository:
    return InvitationRepository(session)


def get_organization_service(
    organization_repository: OrganizationRepository = Depends(get_organization_repository),
    invitation_repository: InvitationRepository = Depends(get_invitation_repository),
    role_repository: RoleRepository = Depends(get_role_repository),
    user_role_repository: UserRoleRepository = Depends(get_user_role_repository),
    user_repository: UserRepository = Depends(get_user_repository),
) -> OrganizationService:
    return OrganizationService(
        organization_repository,
        invitation_repository,
        role_repository,
        user_role_repository,
        user_repository,
    )


async def get_organization(
    org_id: UUID = Path(...),
    repository: OrganizationRepository = Depends(get_organization_repository),
) -> Organization:
    organization = await repository.get_active_by_id(org_id)
    if organization is None:
        raise OrganizationNotFoundException()
    return organization


def require_organization_permission(permission: str) -> Any:
    async def _check_permission(
        org_id: UUID,
        current_user: User = Depends(get_current_active_user),
        auth_service: AuthorizationService = Depends(get_authorization_service),
    ) -> User:
        if not await auth_service.has_permission(
            current_user.id, permission, organization_id=org_id
        ):
            raise AuthorizationException()
        return current_user

    return _check_permission
