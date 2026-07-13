from datetime import datetime
from uuid import UUID

from sqlalchemy import asc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.repository import BaseRepository
from app.common.schemas import PaginationMeta, PaginationParams
from app.scheduling.models import Event


class EventRepository(BaseRepository[Event]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Event)

    async def get_active_by_id(self, event_id: UUID) -> Event | None:
        stmt = (
            select(Event)
            .where(Event.id == event_id, Event.deleted_at.is_(None))
            .options(selectinload(Event.organization))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_organization_and_range(
        self,
        organization_id: UUID,
        start_date: datetime,
        end_date: datetime,
        pagination: PaginationParams,
    ) -> tuple[list[Event], PaginationMeta]:
        stmt = (
            select(Event)
            .where(
                Event.organization_id == organization_id,
                Event.deleted_at.is_(None),
                Event.start_time <= end_date,
                Event.end_time.is_(None) | (Event.end_time >= start_date),
            )
            .options(selectinload(Event.organization))
        )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = stmt.order_by(asc(Event.start_time))
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
