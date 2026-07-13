from typing import Any
from uuid import UUID

from fastapi import Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user
from app.core.database import get_db
from app.core.exceptions import AuthorizationException
from app.organizations.repository import OrganizationRepository
from app.permissions.dependencies import get_authorization_service
from app.permissions.service import AuthorizationService
from app.scheduling.exceptions import EventNotFoundException
from app.scheduling.repository import EventRepository
from app.scheduling.service import EventService
from app.users.models import User


def get_event_repository(session: AsyncSession = Depends(get_db)) -> EventRepository:
    return EventRepository(session)


def get_organization_repository(
    session: AsyncSession = Depends(get_db),
) -> OrganizationRepository:
    return OrganizationRepository(session)


def get_event_service(
    event_repository: EventRepository = Depends(get_event_repository),
    organization_repository: OrganizationRepository = Depends(get_organization_repository),
) -> EventService:
    return EventService(
        event_repository=event_repository,
        organization_repository=organization_repository,
    )


def require_event_permission(permission: str) -> Any:
    async def _check_permission(
        event_id: UUID = Path(...),
        current_user: User = Depends(get_current_active_user),
        auth_service: AuthorizationService = Depends(get_authorization_service),
        event_repository: EventRepository = Depends(get_event_repository),
    ) -> User:
        event = await event_repository.get_active_by_id(event_id)
        if event is None:
            raise EventNotFoundException()
        if not await auth_service.has_permission(
            current_user.id,
            permission,
            organization_id=event.organization_id,
        ):
            raise AuthorizationException()
        return current_user

    return _check_permission


def require_organization_event_permission(permission: str) -> Any:
    async def _check_permission(
        org_id: UUID = Path(...),
        current_user: User = Depends(get_current_active_user),
        auth_service: AuthorizationService = Depends(get_authorization_service),
    ) -> User:
        if not await auth_service.has_permission(
            current_user.id,
            permission,
            organization_id=org_id,
        ):
            raise AuthorizationException()
        return current_user

    return _check_permission
