from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.auth.dependencies import get_current_active_user
from app.common.dependencies import get_pagination
from app.common.responses import success_response
from app.common.schemas import PaginationParams
from app.projects.dependencies import (
    get_project,
    get_project_service,
    get_project_tag_service,
    require_organization_project_permission,
    require_project_permission,
)
from app.projects.models import Project
from app.projects.schemas import (
    ProjectAssigneeAdd,
    ProjectAssigneeRemove,
    ProjectCreate,
    ProjectResponse,
    ProjectTagCreate,
    ProjectTagResponse,
    ProjectUpdate,
)
from app.projects.service import ProjectService, ProjectTagService
from app.users.models import User

router = APIRouter(tags=["projects"])


# ── Tags ──────────────────────────────────────────────────────────────────────

@router.post(
    "/organizations/{org_id}/projects/tags",
    status_code=status.HTTP_201_CREATED,
)
async def create_project_tag(
    org_id: UUID,
    data: ProjectTagCreate,
    current_user: User = Depends(get_current_active_user),
    _: User = Depends(require_organization_project_permission("project:create")),
    service: ProjectTagService = Depends(get_project_tag_service),
) -> dict[str, Any]:
    tag = await service.create(org_id, data, current_user)
    return success_response(
        data=ProjectTagResponse.model_validate(tag),
        message="Tag created successfully.",
    )


@router.get("/organizations/{org_id}/projects/tags")
async def list_project_tags(
    org_id: UUID,
    _: User = Depends(require_organization_project_permission("project:read")),
    service: ProjectTagService = Depends(get_project_tag_service),
) -> dict[str, Any]:
    tags = await service.list_tags(org_id)
    return success_response(data=[ProjectTagResponse.model_validate(t) for t in tags])


@router.delete("/projects/tags/{tag_id}")
async def delete_project_tag(
    tag_id: UUID,
    current_user: User = Depends(get_current_active_user),
    service: ProjectTagService = Depends(get_project_tag_service),
) -> dict[str, Any]:
    await service.delete(tag_id)
    return success_response(message="Tag deleted successfully.")


# ── Projects ──────────────────────────────────────────────────────────────────

@router.post(
    "/organizations/{org_id}/projects",
    status_code=status.HTTP_201_CREATED,
)
async def create_project(
    org_id: UUID,
    data: ProjectCreate,
    current_user: User = Depends(get_current_active_user),
    _: User = Depends(require_organization_project_permission("project:create")),
    service: ProjectService = Depends(get_project_service),
) -> dict[str, Any]:
    project = await service.create(org_id, data, current_user)
    return success_response(
        data=ProjectResponse.model_validate(project),
        message="Project created successfully.",
    )


@router.get("/organizations/{org_id}/projects")
async def list_projects(
    org_id: UUID,
    pagination: PaginationParams = Depends(get_pagination),
    status_filter: str | None = Query(None, alias="status"),
    priority: str | None = Query(None),
    team_id: UUID | None = Query(None),
    search: str | None = Query(None),
    include_archived: bool = Query(False),
    _: User = Depends(require_organization_project_permission("project:read")),
    service: ProjectService = Depends(get_project_service),
) -> dict[str, Any]:
    items, meta = await service.list_projects(
        organization_id=org_id,
        pagination=pagination,
        status=status_filter,
        priority=priority,
        team_id=team_id,
        search=search,
        include_archived=include_archived,
    )
    return success_response(
        data=[ProjectResponse.model_validate(p) for p in items],
        meta={"pagination": meta.model_dump()},
    )


@router.get("/projects/{project_id}")
async def get_project_by_id(
    project: Project = Depends(get_project),
    _: User = Depends(require_project_permission("project:read")),
) -> dict[str, Any]:
    return success_response(data=ProjectResponse.model_validate(project))


@router.patch("/projects/{project_id}")
async def update_project(
    project_id: UUID,
    data: ProjectUpdate,
    current_user: User = Depends(get_current_active_user),
    _: User = Depends(require_project_permission("project:update")),
    service: ProjectService = Depends(get_project_service),
) -> dict[str, Any]:
    project = await service.update(project_id, data, current_user)
    return success_response(
        data=ProjectResponse.model_validate(project),
        message="Project updated successfully.",
    )


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: UUID,
    current_user: User = Depends(get_current_active_user),
    _: User = Depends(require_project_permission("project:delete")),
    service: ProjectService = Depends(get_project_service),
) -> dict[str, Any]:
    await service.delete(project_id, current_user)
    return success_response(message="Project deleted successfully.")


@router.post("/projects/{project_id}/archive")
async def archive_project(
    project_id: UUID,
    current_user: User = Depends(get_current_active_user),
    _: User = Depends(require_project_permission("project:update")),
    service: ProjectService = Depends(get_project_service),
) -> dict[str, Any]:
    project = await service.archive(project_id, current_user)
    return success_response(
        data=ProjectResponse.model_validate(project),
        message="Project archived successfully.",
    )


@router.post("/projects/{project_id}/restore")
async def restore_project(
    project_id: UUID,
    current_user: User = Depends(get_current_active_user),
    _: User = Depends(require_project_permission("project:update")),
    service: ProjectService = Depends(get_project_service),
) -> dict[str, Any]:
    project = await service.restore(project_id, current_user)
    return success_response(
        data=ProjectResponse.model_validate(project),
        message="Project restored successfully.",
    )


# ── Assignees ─────────────────────────────────────────────────────────────────

@router.post("/projects/{project_id}/assignees")
async def add_assignee(
    project_id: UUID,
    data: ProjectAssigneeAdd,
    current_user: User = Depends(get_current_active_user),
    _: User = Depends(require_project_permission("project:update")),
    service: ProjectService = Depends(get_project_service),
) -> dict[str, Any]:
    assignment = await service.add_assignee(project_id, data, current_user)
    return success_response(
        data={"assignment_id": str(assignment.id)},
        message="Assignee added successfully.",
    )


@router.delete("/projects/{project_id}/assignees")
async def remove_assignee(
    project_id: UUID,
    data: ProjectAssigneeRemove,
    current_user: User = Depends(get_current_active_user),
    _: User = Depends(require_project_permission("project:update")),
    service: ProjectService = Depends(get_project_service),
) -> dict[str, Any]:
    await service.remove_assignee(project_id, data, current_user)
    return success_response(message="Assignee removed successfully.")


@router.get("/projects/{project_id}/assignees")
async def list_assignees(
    project_id: UUID,
    _: User = Depends(require_project_permission("project:read")),
    service: ProjectService = Depends(get_project_service),
) -> dict[str, Any]:
    assignees = await service.list_assignees(project_id)
    return success_response(data=assignees)
