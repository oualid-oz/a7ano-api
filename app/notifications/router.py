from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.auth.dependencies import get_current_active_user
from app.common.dependencies import get_pagination
from app.common.responses import success_response
from app.common.schemas import PaginationParams
from app.notifications.dependencies import get_notification_service
from app.notifications.schemas import NotificationResponse
from app.notifications.service import NotificationService
from app.users.models import User

router = APIRouter(tags=["notifications"])


@router.get("/notifications")
async def list_notifications(
    pagination: PaginationParams = Depends(get_pagination),
    unread_only: bool = False,
    current_user: User = Depends(get_current_active_user),
    service: NotificationService = Depends(get_notification_service),
) -> dict[str, Any]:
    items, meta = await service.list_for_user(
        current_user.id, pagination, unread_only=unread_only
    )
    return success_response(
        data=[NotificationResponse.model_validate(n) for n in items],
        meta={"pagination": meta.model_dump()},
    )


@router.post("/notifications/{notification_id}/read", status_code=status.HTTP_200_OK)
async def mark_notification_read(
    notification_id: UUID,
    current_user: User = Depends(get_current_active_user),
    service: NotificationService = Depends(get_notification_service),
) -> dict[str, Any]:
    notification = await service.mark_read(notification_id, current_user)
    return success_response(
        data=NotificationResponse.model_validate(notification),
        message="Notification marked as read.",
    )


@router.post("/notifications/read-all", status_code=status.HTTP_200_OK)
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_active_user),
    service: NotificationService = Depends(get_notification_service),
) -> dict[str, Any]:
    count = await service.mark_all_read(current_user)
    return success_response(
        data={"marked_as_read": count},
        message="All notifications marked as read.",
    )
