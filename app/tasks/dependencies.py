from typing import Any
from uuid import UUID

from fastapi import Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user
from app.core.database import get_db
from app.core.exceptions import AuthorizationException
from app.permissions.dependencies import get_authorization_service
from app.permissions.service import AuthorizationService
from app.projects.dependencies import get_project_repository
from app.projects.repository import ProjectRepository
from app.tasks.exceptions import TaskNotFoundException
from app.tasks.repository import TaskRepository
from app.tasks.service import TaskService
from app.users.dependencies import get_user_repository
from app.users.models import User
from app.users.repository import UserRepository


def get_task_repository(session: AsyncSession = Depends(get_db)) -> TaskRepository:
    return TaskRepository(session)


def get_task_service(
    task_repository: TaskRepository = Depends(get_task_repository),
    project_repository: ProjectRepository = Depends(get_project_repository),
    user_repository: UserRepository = Depends(get_user_repository),
) -> TaskService:
    return TaskService(
        task_repository=task_repository,
        project_repository=project_repository,
        user_repository=user_repository,
    )


def require_task_permission(permission: str) -> Any:
    async def _check_permission(
        task_id: UUID = Path(...),
        current_user: User = Depends(get_current_active_user),
        auth_service: AuthorizationService = Depends(get_authorization_service),
        task_repository: TaskRepository = Depends(get_task_repository),
    ) -> User:
        task = await task_repository.get_active_by_id(task_id)
        if task is None:
            raise TaskNotFoundException()
        if not await auth_service.has_permission(
            current_user.id,
            permission,
            organization_id=task.project.organization_id,
        ):
            raise AuthorizationException()
        return current_user

    return _check_permission
