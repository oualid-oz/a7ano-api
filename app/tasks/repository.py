from uuid import UUID

from sqlalchemy import asc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.repository import BaseRepository
from app.common.schemas import PaginationMeta, PaginationParams
from app.tasks.models import Task


class TaskRepository(BaseRepository[Task]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Task)

    async def get_active_by_id(self, task_id: UUID) -> Task | None:
        stmt = (
            select(Task)
            .where(Task.id == task_id, Task.deleted_at.is_(None))
            .options(selectinload(Task.project), selectinload(Task.assignee))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_project(
        self,
        project_id: UUID,
        pagination: PaginationParams,
        status: str | None = None,
        priority: str | None = None,
        assignee_id: UUID | None = None,
    ) -> tuple[list[Task], PaginationMeta]:
        stmt = select(Task).where(Task.project_id == project_id, Task.deleted_at.is_(None))

        if status:
            stmt = stmt.where(Task.status == status)
        if priority:
            stmt = stmt.where(Task.priority == priority)
        if assignee_id:
            stmt = stmt.where(Task.assignee_id == assignee_id)

        stmt = stmt.options(selectinload(Task.project), selectinload(Task.assignee))

        from sqlalchemy import func

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = stmt.order_by(asc(Task.created_at))
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
