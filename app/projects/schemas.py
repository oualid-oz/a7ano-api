from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

ProjectStatus = Literal["planning", "active", "on_hold", "completed", "cancelled"]
ProjectPriority = Literal["low", "medium", "high", "urgent"]
AssigneeRole = Literal["owner", "manager", "member", "observer"]


class ProjectTagCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    color: str | None = Field(None, max_length=16)


class ProjectTagResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    color: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ProjectTagUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=64)
    color: str | None = Field(None, max_length=16)


class ProjectCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=10000)
    status: ProjectStatus = "active"
    priority: ProjectPriority = "medium"
    due_date: datetime | None = None
    team_id: UUID | None = None
    tag_ids: list[UUID] = Field(default_factory=list)


class ProjectUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=10000)
    status: ProjectStatus | None = None
    priority: ProjectPriority | None = None
    due_date: datetime | None = None
    team_id: UUID | None = None
    tag_ids: list[UUID] | None = None


class AssigneeResponse(BaseModel):
    user_id: UUID
    full_name: str | None
    email: str
    role: str

    model_config = {"from_attributes": True}


class ProjectResponse(BaseModel):
    id: UUID
    organization_id: UUID
    team_id: UUID | None
    owner_id: UUID
    title: str
    description: str | None
    status: str
    priority: str
    due_date: datetime | None
    archived_at: datetime | None
    is_archived: bool
    tags: list[ProjectTagResponse]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectAssigneeAdd(BaseModel):
    user_id: UUID
    role: AssigneeRole = "member"


class ProjectAssigneeRemove(BaseModel):
    user_id: UUID
