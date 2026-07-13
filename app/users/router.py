from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user
from app.common.responses import success_response
from app.core.database import get_db
from app.users.dependencies import get_user_service
from app.users.models import User
from app.users.schemas import UserResponse, UserUpdate
from app.users.service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("")
async def list_active_users(
    search: str | None = Query(None),
    current_user: User = Depends(get_current_active_user),
    service: UserService = Depends(get_user_service),
) -> dict[str, Any]:
    users = await service.list_active(search)
    return success_response(
        data=[UserResponse.model_validate(u) for u in users],
    )


@router.get("/me")
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    return success_response(data=UserResponse.model_validate(current_user))


@router.patch("/me")
async def update_current_user_profile(
    data: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    service: UserService = Depends(get_user_service),
) -> dict[str, Any]:
    updated = await service.update_profile(current_user, data)
    return success_response(data=UserResponse.model_validate(updated))


@router.get("/me/stats")
async def get_dashboard_stats(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    from app.memos.models import Memo
    from app.organizations.models import Organization
    from app.permissions.models import UserRole
    from app.projects.models import Project
    from app.tasks.models import Task
    from app.teams.models import Team

    user_id = current_user.id

    # orgs the user owns or is a member of
    owned_org_ids = select(Organization.id).where(
        Organization.owner_id == user_id,
        Organization.deleted_at.is_(None),
    )
    member_org_ids = select(UserRole.organization_id).where(
        UserRole.user_id == user_id,
        UserRole.organization_id.isnot(None),
    )
    all_org_ids_stmt = owned_org_ids.union(member_org_ids)

    org_count_result = await db.execute(
        select(func.count()).select_from(all_org_ids_stmt.subquery())
    )
    org_count = org_count_result.scalar_one()

    # projects in those orgs
    org_subq = all_org_ids_stmt.subquery()
    project_count_result = await db.execute(
        select(func.count(Project.id)).where(
            Project.organization_id.in_(select(org_subq)),
            Project.deleted_at.is_(None),
        )
    )
    project_count = project_count_result.scalar_one()

    # teams in those orgs
    team_count_result = await db.execute(
        select(func.count(Team.id)).where(
            Team.organization_id.in_(select(org_subq)),
            Team.deleted_at.is_(None),
        )
    )
    team_count = team_count_result.scalar_one()

    # memos in those orgs
    memo_count_result = await db.execute(
        select(func.count(Memo.id)).where(
            Memo.organization_id.in_(select(org_subq)),
            Memo.deleted_at.is_(None),
        )
    )
    memo_count = memo_count_result.scalar_one()

    # projects by status (for chart)
    status_rows = await db.execute(
        select(Project.status, func.count(Project.id))
        .where(
            Project.organization_id.in_(select(org_subq)),
            Project.deleted_at.is_(None),
        )
        .group_by(Project.status)
    )
    projects_by_status = [{"status": row[0], "count": row[1]} for row in status_rows.all()]

    # tasks by status (for chart)
    task_status_rows = await db.execute(
        select(Task.status, func.count(Task.id))
        .where(
            Task.project_id.in_(
                select(Project.id).where(
                    Project.organization_id.in_(select(org_subq)),
                    Project.deleted_at.is_(None),
                )
            ),
            Task.deleted_at.is_(None),
        )
        .group_by(Task.status)
    )
    tasks_by_status = [{"status": row[0], "count": row[1]} for row in task_status_rows.all()]

    return success_response(
        data={
            "organizations": org_count,
            "projects": project_count,
            "teams": team_count,
            "memos": memo_count,
            "projects_by_status": projects_by_status,
            "tasks_by_status": tasks_by_status,
        }
    )
