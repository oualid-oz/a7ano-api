from uuid import UUID

from pydantic import BaseModel, Field


class PermissionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    resource: str = Field(..., min_length=1, max_length=64)
    action: str = Field(..., min_length=1, max_length=64)
    description: str | None = Field(None, max_length=255)


class PermissionResponse(BaseModel):
    id: UUID
    name: str
    resource: str
    action: str
    description: str | None

    model_config = {"from_attributes": True}


class RoleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    description: str | None = Field(None, max_length=255)
    permission_names: list[str] = Field(default_factory=list)


class RoleUpdate(BaseModel):
    description: str | None = Field(None, max_length=255)
    permission_names: list[str] | None = None


class RoleResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    is_system: bool
    permissions: list[PermissionResponse]

    model_config = {"from_attributes": True}


class UserRoleAssign(BaseModel):
    user_id: UUID
    role_id: UUID
    organization_id: UUID | None = None
    team_id: UUID | None = None


class UserRoleRemove(BaseModel):
    user_id: UUID
    role_id: UUID
    organization_id: UUID | None = None
    team_id: UUID | None = None


class UserRoleResponse(BaseModel):
    id: UUID
    user_id: UUID
    role_id: UUID
    role_name: str
    organization_id: UUID | None
    team_id: UUID | None

    model_config = {"from_attributes": True}
