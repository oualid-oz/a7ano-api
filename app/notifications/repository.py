from typing import Any
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.repository import BaseRepository
from app.common.schemas import PaginationMeta, PaginationParams
from app.notifications.models import Notification


class NotificationRepository(BaseRepository[Notification]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Notification)

    async def list_by_user(
        self,
        user_id: UUID,
        pagination: PaginationParams,
        unread_only: bool = False,
    ) -> tuple[list[Notification], PaginationMeta]:
        filters: dict[str, Any] = {"user_id": user_id}
        if unread_only:
            filters["is_read"] = False
        return await self.list(
            pagination,
            filters=filters,
            sort_field="created_at",
            sort_desc=True,
        )

    async def mark_read(self, notification_id: UUID) -> Notification | None:
        notification = await self.get(notification_id)
        if notification is None or notification.deleted_at is not None:
            return None
        notification.is_read = True
        await self._session.flush()
        await self._session.refresh(notification)
        return notification

    async def mark_all_read(self, user_id: UUID) -> int:
        stmt = (
            update(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
                Notification.deleted_at.is_(None),
            )
            .values(is_read=True)
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return int(result.rowcount)
