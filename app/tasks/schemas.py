from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

TaskStatus = Literal["todo", "in_progress", "done", "cancelled"]
TaskPriority = Literal["low", "medium", "high", "urgent"]


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=10000)
    status: TaskStatus = "todo"
    priority: TaskPriority = "medium"
    due_date: datetime | None = None
    assignee_id: UUID | None = None


class TaskUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=10000)
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    due_date: datetime | None = None
    assignee_id: UUID | None = None


class TaskResponse(BaseModel):
    id: UUID
    project_id: UUID
    title: str
    description: str | None
    status: str
    priority: str
    due_date: datetime | None
    assignee_id: UUID | None
    created_by: UUID | None
    updated_by: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
