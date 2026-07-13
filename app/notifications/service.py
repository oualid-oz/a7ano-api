from uuid import UUID

from app.common.schemas import PaginationMeta, PaginationParams
from app.core.exceptions import AuthorizationException
from app.core.logging import get_logger
from app.notifications.exceptions import NotificationNotFoundException
from app.notifications.models import Notification
from app.notifications.repository import NotificationRepository
from app.notifications.schemas import NotificationCreate
from app.users.models import User

logger = get_logger(__name__)


class NotificationService:
    def __init__(self, repository: NotificationRepository) -> None:
        self._repository = repository

    async def create(self, data: NotificationCreate) -> Notification:
        logger.info(
            "Creating notification", extra={"user_id": str(data.user_id), "title": data.title}
        )
        notification = Notification(
            user_id=data.user_id,
            title=data.title,
            body=data.body,
            notification_type=data.notification_type,
            resource_type=data.resource_type,
            resource_id=data.resource_id,
        )
        notification = await self._repository.create(notification)
        logger.info(
            "Notification created",
            extra={"notification_id": str(notification.id), "user_id": str(data.user_id)},
        )
        return notification

    async def list_for_user(
        self,
        user_id: UUID,
        pagination: PaginationParams,
        unread_only: bool = False,
    ) -> tuple[list[Notification], PaginationMeta]:
        logger.info(
            "Listing notifications for user",
            extra={"user_id": str(user_id), "page": pagination.page, "unread_only": unread_only},
        )
        items, meta = await self._repository.list_by_user(user_id, pagination, unread_only)
        logger.info(
            "Notification list response",
            extra={"user_id": str(user_id), "total": meta.total, "unread_only": unread_only},
        )
        return items, meta

    async def mark_read(self, notification_id: UUID, current_user: User) -> Notification:
        logger.info(
            "Marking notification as read",
            extra={"notification_id": str(notification_id), "user_id": str(current_user.id)},
        )
        notification = await self._repository.get(notification_id)
        if notification is None or notification.deleted_at is not None:
            logger.warning(
                "Mark-read failed: notification not found",
                extra={"notification_id": str(notification_id)},
            )
            raise NotificationNotFoundException()
        if notification.user_id != current_user.id:
            logger.warning(
                "Mark-read denied: notification belongs to another user",
                extra={"notification_id": str(notification_id), "user_id": str(current_user.id)},
            )
            raise AuthorizationException()
        notification.is_read = True
        await self._repository._session.flush()
        await self._repository._session.refresh(notification)
        logger.info(
            "Notification marked as read",
            extra={"notification_id": str(notification_id)},
        )
        return notification

    async def mark_all_read(self, current_user: User) -> int:
        logger.info("Marking all notifications as read", extra={"user_id": str(current_user.id)})
        count = await self._repository.mark_all_read(current_user.id)
        logger.info(
            "All notifications marked as read",
            extra={"user_id": str(current_user.id), "count": count},
        )
        return count

    async def dispatch(
        self,
        user_id: UUID,
        title: str,
        body: str | None = None,
        notification_type: str = "info",
        resource_type: str | None = None,
        resource_id: str | None = None,
    ) -> Notification:
        logger.info(
            "Dispatching notification",
            extra={
                "user_id": str(user_id),
                "title": title,
                "notification_type": notification_type,
                "resource_type": resource_type,
                "resource_id": resource_id,
            },
        )
        data = NotificationCreate(
            user_id=user_id,
            title=title,
            body=body,
            notification_type=notification_type,
            resource_type=resource_type,
            resource_id=resource_id,
        )
        return await self.create(data)
