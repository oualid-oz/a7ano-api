from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class EventCreate(BaseModel):
    organization_id: UUID | None = None
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=10000)
    start_time: datetime
    end_time: datetime | None = None
    location: str | None = Field(None, max_length=255)
    color: str | None = Field(None, max_length=16)
    all_day: bool = False

    @model_validator(mode="after")
    def check_end_time(self) -> "EventCreate":
        if self.end_time is not None and self.end_time < self.start_time:
            raise ValueError("End time must be after start time.")
        if self.end_time is not None and self.end_time.date() != self.start_time.date():
            raise ValueError("Event must start and end on the same day.")
        return self


class EventUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=10000)
    start_time: datetime | None = None
    end_time: datetime | None = None
    location: str | None = Field(None, max_length=255)
    color: str | None = Field(None, max_length=16)
    all_day: bool | None = None

    @model_validator(mode="after")
    def check_end_time(self) -> "EventUpdate":
        if (
            self.end_time is not None
            and self.start_time is not None
            and self.end_time < self.start_time
        ):
            raise ValueError("End time must be after start time.")
        if (
            self.end_time is not None
            and self.start_time is not None
            and self.end_time.date() != self.start_time.date()
        ):
            raise ValueError("Event must start and end on the same day.")
        return self


class EventResponse(BaseModel):
    id: UUID
    organization_id: UUID
    title: str
    description: str | None
    start_time: datetime
    end_time: datetime | None
    location: str | None
    color: str | None
    all_day: bool
    created_by: UUID | None
    updated_by: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
