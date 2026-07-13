from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.auth.dependencies import get_current_active_user
from app.common.dependencies import get_pagination
from app.common.responses import success_response
from app.common.schemas import PaginationParams
from app.projects.dependencies import require_project_permission
from app.tasks.dependencies import (
    get_task_service,
    require_task_permission,
)
from app.tasks.schemas import TaskCreate, TaskResponse, TaskUpdate
from app.tasks.service import TaskService
from app.users.models import User

router = APIRouter(tags=["tasks"])


@router.post(
    "/projects/{project_id}/tasks",
    status_code=status.HTTP_201_CREATED,
)
async def create_task(
    project_id: UUID,
    data: TaskCreate,
    current_user: User = Depends(get_current_active_user),
    _: User = Depends(require_project_permission("project:update")),
    service: TaskService = Depends(get_task_service),
) -> dict[str, Any]:
    task = await service.create(project_id, data, current_user)
    return success_response(
        data=TaskResponse.model_validate(task),
        message="Task created successfully.",
    )


@router.get("/projects/{project_id}/tasks")
async def list_tasks(
    project_id: UUID,
    pagination: PaginationParams = Depends(get_pagination),
    status_filter: str | None = Query(None, alias="status"),
    priority: str | None = Query(None),
    assignee_id: UUID | None = Query(None),
    current_user: User = Depends(get_current_active_user),
    _: User = Depends(require_project_permission("project:read")),
    service: TaskService = Depends(get_task_service),
) -> dict[str, Any]:
    items, meta = await service.list_tasks(
        project_id=project_id,
        pagination=pagination,
        status=status_filter,
        priority=priority,
        assignee_id=assignee_id,
    )
    return success_response(
        data=[TaskResponse.model_validate(t) for t in items],
        meta={"pagination": meta.model_dump()},
    )


@router.get("/tasks/{task_id}")
async def get_task_by_id(
    task_id: UUID,
    current_user: User = Depends(get_current_active_user),
    _: User = Depends(require_task_permission("project:read")),
    service: TaskService = Depends(get_task_service),
) -> dict[str, Any]:
    task = await service.get(task_id)
    return success_response(data=TaskResponse.model_validate(task))


@router.patch("/tasks/{task_id}")
async def update_task(
    task_id: UUID,
    data: TaskUpdate,
    current_user: User = Depends(get_current_active_user),
    _: User = Depends(require_task_permission("project:update")),
    service: TaskService = Depends(get_task_service),
) -> dict[str, Any]:
    task = await service.update(task_id, data, current_user)
    return success_response(
        data=TaskResponse.model_validate(task),
        message="Task updated successfully.",
    )


@router.delete("/tasks/{task_id}")
async def delete_task(
    task_id: UUID,
    current_user: User = Depends(get_current_active_user),
    _: User = Depends(require_task_permission("project:update")),
    service: TaskService = Depends(get_task_service),
) -> dict[str, Any]:
    await service.delete(task_id, current_user)
    return success_response(message="Task deleted successfully.")
