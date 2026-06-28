from uuid import UUID

from app.common.schemas import PaginationMeta, PaginationParams
from app.core.exceptions import AuthorizationException
from app.notifications.exceptions import NotificationNotFoundException
from app.notifications.models import Notification
from app.notifications.repository import NotificationRepository
from app.notifications.schemas import NotificationCreate
from app.users.models import User


class NotificationService:
    def __init__(self, repository: NotificationRepository) -> None:
        self._repository = repository

    async def create(self, data: NotificationCreate) -> Notification:
        notification = Notification(
            user_id=data.user_id,
            title=data.title,
            body=data.body,
            notification_type=data.notification_type,
            resource_type=data.resource_type,
            resource_id=data.resource_id,
        )
        return await self._repository.create(notification)

    async def list_for_user(
        self,
        user_id: UUID,
        pagination: PaginationParams,
        unread_only: bool = False,
    ) -> tuple[list[Notification], PaginationMeta]:
        return await self._repository.list_by_user(user_id, pagination, unread_only)

    async def mark_read(self, notification_id: UUID, current_user: User) -> Notification:
        notification = await self._repository.get(notification_id)
        if notification is None or notification.deleted_at is not None:
            raise NotificationNotFoundException()
        if notification.user_id != current_user.id:
            raise AuthorizationException()
        notification.is_read = True
        await self._repository._session.flush()
        await self._repository._session.refresh(notification)
        return notification

    async def mark_all_read(self, current_user: User) -> int:
        return await self._repository.mark_all_read(current_user.id)

    async def dispatch(
        self,
        user_id: UUID,
        title: str,
        body: str | None = None,
        notification_type: str = "info",
        resource_type: str | None = None,
        resource_id: str | None = None,
    ) -> Notification:
        data = NotificationCreate(
            user_id=user_id,
            title=title,
            body=body,
            notification_type=notification_type,
            resource_type=resource_type,
            resource_id=resource_id,
        )
        return await self.create(data)
