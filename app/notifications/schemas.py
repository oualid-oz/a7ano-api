from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    body: str | None
    notification_type: str
    is_read: bool
    resource_type: str | None
    resource_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationCreate(BaseModel):
    user_id: UUID
    title: str
    body: str | None = None
    notification_type: str = "info"
    resource_type: str | None = None
    resource_id: str | None = None
