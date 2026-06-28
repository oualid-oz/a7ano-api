from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class TeamCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)


class TeamUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)


class TeamResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TeamMemberAdd(BaseModel):
    user_id: UUID
    role_id: UUID


class TeamMemberRemove(BaseModel):
    user_id: UUID
    role_id: UUID


class TeamMemberResponse(BaseModel):
    user_id: UUID
    full_name: str | None
    email: str
    role_id: UUID
    role_name: str

    model_config = {"from_attributes": True}
