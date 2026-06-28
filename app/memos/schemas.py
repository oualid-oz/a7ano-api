from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class MemoFolderCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    parent_id: UUID | None = None


class MemoFolderUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    parent_id: UUID | None = None


class MemoFolderResponse(BaseModel):
    id: UUID
    organization_id: UUID
    owner_id: UUID
    name: str
    parent_id: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MemoTagCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    color: str | None = Field(None, max_length=16)


class MemoTagUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=64)
    color: str | None = Field(None, max_length=16)


class MemoTagResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    color: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class MemoCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    content: str | None = Field(None, max_length=50000)
    folder_id: UUID | None = None
    is_pinned: bool = False
    is_favorite: bool = False
    tag_ids: list[UUID] = Field(default_factory=list)


class MemoUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    content: str | None = Field(None, max_length=50000)
    folder_id: UUID | None = None
    is_pinned: bool | None = None
    is_favorite: bool | None = None
    tag_ids: list[UUID] | None = None


class MemoResponse(BaseModel):
    id: UUID
    organization_id: UUID
    owner_id: UUID
    folder_id: UUID | None
    title: str
    content: str | None
    is_pinned: bool
    is_favorite: bool
    tags: list[MemoTagResponse]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MemoVersionResponse(BaseModel):
    id: UUID
    memo_id: UUID
    version_number: int
    content: str | None
    created_by: UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}
