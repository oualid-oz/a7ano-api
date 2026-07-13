from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str | None = Field(None, max_length=128)
    description: str | None = Field(None, max_length=2000)
    logo_url: str | None = Field(None, max_length=512)


class OrganizationUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)
    logo_url: str | None = Field(None, max_length=512)
    is_active: bool | None = None


class OrganizationResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    description: str | None
    logo_url: str | None
    is_active: bool
    owner_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class InvitationCreate(BaseModel):
    email: EmailStr
    role_id: UUID


class InvitationResponse(BaseModel):
    id: UUID
    email: str
    token: str
    organization_id: UUID
    invited_by_id: UUID
    role_id: UUID
    status: str
    expires_at: datetime
    accepted_at: datetime | None
    accepted_by_id: UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class InvitationAccept(BaseModel):
    token: str


class MemberResponse(BaseModel):
    user_id: UUID
    full_name: str | None
    email: str
    role_id: UUID
    role_name: str

    model_config = {"from_attributes": True}


class MemberRoleUpdate(BaseModel):
    role_id: UUID
