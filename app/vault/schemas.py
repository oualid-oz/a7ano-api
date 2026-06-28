from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class VaultCategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    description: str | None = Field(None, max_length=255)
    icon: str | None = Field(None, max_length=64)


class VaultCategoryResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    description: str | None
    icon: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class VaultTagCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    color: str | None = Field(None, max_length=16)


class VaultTagResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    color: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class VaultEntryCreate(BaseModel):
    entry_type: str = Field("password", max_length=32)
    title: str = Field(..., min_length=1, max_length=255)
    username: str | None = None
    password: str | None = None
    email: str | None = None
    url: str | None = Field(None, max_length=512)
    notes: str | None = None
    category_id: UUID | None = None
    tag_ids: list[UUID] = Field(default_factory=list)
    expires_at: datetime | None = None


class VaultEntryUpdate(BaseModel):
    entry_type: str | None = Field(None, max_length=32)
    title: str | None = Field(None, min_length=1, max_length=255)
    username: str | None = None
    password: str | None = None
    email: str | None = None
    url: str | None = Field(None, max_length=512)
    notes: str | None = None
    category_id: UUID | None = None
    tag_ids: list[UUID] | None = None
    expires_at: datetime | None = None


class VaultEntryResponse(BaseModel):
    id: UUID
    organization_id: UUID | None
    owner_id: UUID
    category_id: UUID | None
    entry_type: str
    title: str
    username: str | None
    password: str | None
    email: str | None
    url: str | None
    notes: str | None
    expires_at: datetime | None
    last_accessed_at: datetime | None
    tags: list[VaultTagResponse]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class VaultEntrySummaryResponse(BaseModel):
    id: UUID
    organization_id: UUID | None
    owner_id: UUID
    category_id: UUID | None
    entry_type: str
    title: str
    username: str | None
    email: str | None
    url: str | None
    expires_at: datetime | None
    last_accessed_at: datetime | None
    tags: list[VaultTagResponse]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class VaultShareCreate(BaseModel):
    shared_with_user_id: UUID | None = None
    shared_with_team_id: UUID | None = None
    permission: str = Field("read", max_length=16)
    expires_at: datetime | None = None


class VaultShareResponse(BaseModel):
    id: UUID
    entry_id: UUID
    shared_with_user_id: UUID | None
    shared_with_team_id: UUID | None
    permission: str
    expires_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class VaultAccessLogResponse(BaseModel):
    id: UUID
    entry_id: UUID
    user_id: UUID
    action: str
    ip_address: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
