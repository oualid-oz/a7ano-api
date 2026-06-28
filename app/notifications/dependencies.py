from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.notifications.repository import NotificationRepository
from app.notifications.service import NotificationService


def get_notification_repository(
    session: AsyncSession = Depends(get_db),
) -> NotificationRepository:
    return NotificationRepository(session)


def get_notification_service(
    repo: NotificationRepository = Depends(get_notification_repository),
) -> NotificationService:
    return NotificationService(repo)
