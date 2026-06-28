from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AuditEventCreate(BaseModel):
    actor_id: UUID | None = None
    action: str
    resource_type: str
    resource_id: str | None = None
    organization_id: UUID | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    metadata_: dict | None = Field(None, alias="metadata")

    model_config = {"populate_by_name": True}


class AuditEventResponse(BaseModel):
    id: UUID
    actor_id: UUID | None
    action: str
    resource_type: str
    resource_id: str | None
    organization_id: UUID | None
    ip_address: str | None
    user_agent: str | None
    metadata_: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
