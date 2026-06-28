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
from app.projects.exceptions import ProjectNotFoundException
from app.projects.models import Project
from app.projects.repository import (
    ProjectAssignmentRepository,
    ProjectRepository,
    ProjectTagRepository,
)
from app.projects.service import ProjectService, ProjectTagService
from app.users.dependencies import get_user_repository
from app.users.models import User
from app.users.repository import UserRepository


def get_project_repository(session: AsyncSession = Depends(get_db)) -> ProjectRepository:
    return ProjectRepository(session)


def get_project_tag_repository(session: AsyncSession = Depends(get_db)) -> ProjectTagRepository:
    return ProjectTagRepository(session)


def get_project_assignment_repository(
    session: AsyncSession = Depends(get_db),
) -> ProjectAssignmentRepository:
    return ProjectAssignmentRepository(session)


def get_organization_repository(session: AsyncSession = Depends(get_db)) -> OrganizationRepository:
    return OrganizationRepository(session)


def get_project_tag_service(
    tag_repository: ProjectTagRepository = Depends(get_project_tag_repository),
    organization_repository: OrganizationRepository = Depends(get_organization_repository),
) -> ProjectTagService:
    return ProjectTagService(tag_repository, organization_repository)


def get_project_service(
    project_repository: ProjectRepository = Depends(get_project_repository),
    tag_repository: ProjectTagRepository = Depends(get_project_tag_repository),
    assignment_repository: ProjectAssignmentRepository = Depends(
        get_project_assignment_repository
    ),
    organization_repository: OrganizationRepository = Depends(get_organization_repository),
    user_repository: UserRepository = Depends(get_user_repository),
) -> ProjectService:
    return ProjectService(
        project_repository,
        tag_repository,
        assignment_repository,
        organization_repository,
        user_repository,
    )


async def get_project(
    project_id: UUID = Path(...),
    repository: ProjectRepository = Depends(get_project_repository),
) -> Project:
    project = await repository.get_active_by_id(project_id)
    if project is None:
        raise ProjectNotFoundException()
    return project


def require_project_permission(permission: str) -> Any:
    async def _check_permission(
        project_id: UUID,
        current_user: User = Depends(get_current_active_user),
        auth_service: AuthorizationService = Depends(get_authorization_service),
        project_repository: ProjectRepository = Depends(get_project_repository),
    ) -> User:
        project = await project_repository.get_active_by_id(project_id)
        if project is None:
            raise ProjectNotFoundException()
        if not await auth_service.has_permission(
            current_user.id,
            permission,
            organization_id=project.organization_id,
        ):
            raise AuthorizationException()
        return current_user

    return _check_permission


def require_organization_project_permission(permission: str) -> Any:
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
