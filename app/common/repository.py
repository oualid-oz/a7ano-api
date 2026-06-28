from typing import Any
from uuid import UUID

from sqlalchemy import asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.models import BaseModel
from app.common.schemas import PaginationMeta, PaginationParams
from app.core.exceptions import ResourceNotFoundException


class BaseRepository[T: BaseModel]:
    def __init__(self, session: AsyncSession, model: type[T]) -> None:
        self._session = session
        self._model = model

    @property
    def session(self) -> AsyncSession:
        return self._session

    async def get(self, obj_id: UUID) -> T | None:
        return await self._session.get(self._model, obj_id)

    async def get_or_404(self, obj_id: UUID) -> T:
        obj = await self.get(obj_id)
        if obj is None or obj.deleted_at is not None:
            raise ResourceNotFoundException()
        return obj

    async def list(
        self,
        pagination: PaginationParams,
        filters: dict[str, Any] | None = None,
        sort_field: str | None = None,
        sort_desc: bool = True,
    ) -> tuple[list[T], PaginationMeta]:
        filters = filters or {}
        stmt = select(self._model).where(self._model.deleted_at.is_(None))

        for key, value in filters.items():
            if hasattr(self._model, key) and value is not None:
                column = getattr(self._model, key)
                stmt = stmt.where(column == value)

        sort_attr = sort_field or "created_at"
        if not hasattr(self._model, sort_attr):
            sort_attr = "created_at"
        sort_column = getattr(self._model, sort_attr)
        stmt = stmt.order_by(desc(sort_column) if sort_desc else asc(sort_column))

        count_stmt = select(func.count()).select_from(self._model)
        if stmt.whereclause is not None:
            count_stmt = count_stmt.where(stmt.whereclause)
        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar_one()

        offset = (pagination.page - 1) * pagination.page_size
        stmt = stmt.offset(offset).limit(pagination.page_size)
        result = await self._session.execute(stmt)
        items = result.scalars().all()

        pages = (total + pagination.page_size - 1) // pagination.page_size
        meta = PaginationMeta(
            page=pagination.page,
            page_size=pagination.page_size,
            total=total,
            pages=pages or 1,
        )
        return list(items), meta

    async def create(self, obj: T) -> T:
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    async def update(self, obj: T, data: dict[str, Any]) -> T:
        for key, value in data.items():
            if hasattr(obj, key):
                setattr(obj, key, value)
        obj.bump_version()
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    async def delete_soft(self, obj: T) -> T:
        obj.soft_delete()
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    async def delete_hard(self, obj: T) -> None:
        await self._session.delete(obj)
        await self._session.flush()
