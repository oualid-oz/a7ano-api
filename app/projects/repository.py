from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.repository import BaseRepository
from app.common.schemas import PaginationMeta, PaginationParams
from app.projects.models import Project, ProjectAssignment, ProjectTag


class ProjectRepository(BaseRepository[Project]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Project)

    async def get_active_by_id(self, project_id: UUID) -> Project | None:
        stmt = (
            select(Project)
            .where(Project.id == project_id, Project.deleted_at.is_(None))
            .options(
                selectinload(Project.tags),
                selectinload(Project.assignees),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_organization(
        self,
        organization_id: UUID,
        pagination: PaginationParams,
        status: str | None = None,
        priority: str | None = None,
        team_id: UUID | None = None,
        search: str | None = None,
        include_archived: bool = False,
    ) -> tuple[list[Project], PaginationMeta]:
        filters: dict = {"organization_id": organization_id}
        if status:
            filters["status"] = status
        if priority:
            filters["priority"] = priority
        if team_id:
            filters["team_id"] = team_id
        if not include_archived:
            filters["archived_at"] = None

        stmt = select(Project).where(Project.deleted_at.is_(None))
        for key, value in filters.items():
            if key == "archived_at":
                stmt = stmt.where(Project.archived_at.is_(None))
            elif hasattr(Project, key) and value is not None:
                stmt = stmt.where(getattr(Project, key) == value)

        if search:
            stmt = stmt.where(Project.title.ilike(f"%{search}%"))

        stmt = stmt.options(
            selectinload(Project.tags),
            selectinload(Project.assignees),
        )

        from sqlalchemy import desc, func

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = stmt.order_by(desc(Project.created_at))
        offset = (pagination.page - 1) * pagination.page_size
        stmt = stmt.offset(offset).limit(pagination.page_size)
        result = await self._session.execute(stmt)
        items = list(result.scalars().all())

        pages = (total + pagination.page_size - 1) // pagination.page_size
        meta = PaginationMeta(
            page=pagination.page,
            page_size=pagination.page_size,
            total=total,
            pages=pages or 1,
        )
        return items, meta


class ProjectTagRepository(BaseRepository[ProjectTag]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ProjectTag)

    async def get_by_name_and_org(self, name: str, organization_id: UUID) -> ProjectTag | None:
        stmt = select(ProjectTag).where(
            ProjectTag.name == name,
            ProjectTag.organization_id == organization_id,
            ProjectTag.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_organization(self, organization_id: UUID) -> list[ProjectTag]:
        stmt = select(ProjectTag).where(
            ProjectTag.organization_id == organization_id,
            ProjectTag.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_many_by_ids(self, tag_ids: list[UUID]) -> list[ProjectTag]:
        if not tag_ids:
            return []
        stmt = select(ProjectTag).where(
            ProjectTag.id.in_(tag_ids),
            ProjectTag.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())


class ProjectAssignmentRepository(BaseRepository[ProjectAssignment]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ProjectAssignment)

    async def get_assignment(
        self, project_id: UUID, user_id: UUID
    ) -> ProjectAssignment | None:
        stmt = select(ProjectAssignment).where(
            and_(
                ProjectAssignment.project_id == project_id,
                ProjectAssignment.user_id == user_id,
                ProjectAssignment.deleted_at.is_(None),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_project(self, project_id: UUID) -> list[ProjectAssignment]:
        stmt = select(ProjectAssignment).where(
            ProjectAssignment.project_id == project_id,
            ProjectAssignment.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
