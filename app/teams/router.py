from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.auth.dependencies import get_current_active_user
from app.common.dependencies import get_pagination
from app.common.responses import success_response
from app.common.schemas import PaginationParams
from app.organizations.dependencies import require_organization_permission
from app.teams.dependencies import (
    get_team,
    get_team_service,
    require_team_permission,
)
from app.teams.models import Team
from app.teams.schemas import (
    TeamCreate,
    TeamMemberAdd,
    TeamMemberRemove,
    TeamResponse,
    TeamUpdate,
)
from app.teams.service import TeamService
from app.users.models import User

router = APIRouter(tags=["teams"])


@router.post("/organizations/{org_id}/teams", status_code=status.HTTP_201_CREATED)
async def create_team(
    org_id: UUID,
    data: TeamCreate,
    current_user: User = Depends(get_current_active_user),
    _: User = Depends(require_organization_permission("team:create")),
    service: TeamService = Depends(get_team_service),
) -> dict[str, Any]:
    team = await service.create(org_id, data, current_user)
    return success_response(
        data=TeamResponse.model_validate(team),
        message="Team created successfully.",
    )


@router.get("/organizations/{org_id}/teams")
async def list_teams(
    org_id: UUID,
    pagination: PaginationParams = Depends(get_pagination),
    _: User = Depends(require_organization_permission("team:read")),
    service: TeamService = Depends(get_team_service),
) -> dict[str, Any]:
    items, meta = await service.list_teams(org_id, pagination)
    return success_response(
        data=[TeamResponse.model_validate(t) for t in items],
        meta={"pagination": meta.model_dump()},
    )


@router.get("/teams/{team_id}")
async def get_team_by_id(
    team: Team = Depends(get_team),
    _: User = Depends(require_team_permission("team:read")),
) -> dict[str, Any]:
    return success_response(data=TeamResponse.model_validate(team))


@router.patch("/teams/{team_id}")
async def update_team(
    team_id: UUID,
    data: TeamUpdate,
    current_user: User = Depends(get_current_active_user),
    _: User = Depends(require_team_permission("team:update")),
    service: TeamService = Depends(get_team_service),
) -> dict[str, Any]:
    team = await service.update(team_id, data, current_user)
    return success_response(
        data=TeamResponse.model_validate(team),
        message="Team updated successfully.",
    )


@router.delete("/teams/{team_id}")
async def delete_team(
    team_id: UUID,
    current_user: User = Depends(get_current_active_user),
    _: User = Depends(require_team_permission("team:delete")),
    service: TeamService = Depends(get_team_service),
) -> dict[str, Any]:
    await service.delete(team_id, current_user)
    return success_response(message="Team deleted successfully.")


@router.post("/teams/{team_id}/members")
async def add_team_member(
    team_id: UUID,
    data: TeamMemberAdd,
    current_user: User = Depends(get_current_active_user),
    _: User = Depends(require_team_permission("team:update")),
    service: TeamService = Depends(get_team_service),
) -> dict[str, Any]:
    membership = await service.add_member(team_id, data, current_user)
    return success_response(
        data={"membership_id": str(membership.id)},
        message="Member added successfully.",
    )


@router.delete("/teams/{team_id}/members")
async def remove_team_member(
    team_id: UUID,
    data: TeamMemberRemove,
    current_user: User = Depends(get_current_active_user),
    _: User = Depends(require_team_permission("team:update")),
    service: TeamService = Depends(get_team_service),
) -> dict[str, Any]:
    await service.remove_member(team_id, data, current_user)
    return success_response(message="Member removed successfully.")


@router.get("/teams/{team_id}/members")
async def list_team_members(
    team_id: UUID,
    _: User = Depends(require_team_permission("team:read")),
    service: TeamService = Depends(get_team_service),
) -> dict[str, Any]:
    members = await service.list_members(team_id)
    return success_response(data=members)
