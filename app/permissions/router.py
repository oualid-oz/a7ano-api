from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.auth.dependencies import get_current_active_user
from app.common.dependencies import get_pagination
from app.common.responses import success_response
from app.common.schemas import PaginationParams
from app.permissions.dependencies import (
    get_authorization_service,
    get_permission_service,
    get_role_service,
    require_permission,
)
from app.permissions.schemas import (
    PermissionCreate,
    PermissionResponse,
    RoleCreate,
    RoleResponse,
    RoleUpdate,
    UserRoleAssign,
    UserRoleRemove,
    UserRoleResponse,
)
from app.permissions.service import (
    AuthorizationService,
    PermissionService,
    RoleService,
)
from app.users.models import User

router = APIRouter(tags=["permissions"])


@router.get("/permissions")
async def list_permissions(
    pagination: PaginationParams = Depends(get_pagination),
    service: PermissionService = Depends(get_permission_service),
    _: User = Depends(require_permission("role:manage")),
) -> dict[str, Any]:
    items, meta = await service.list_permissions(pagination)
    return success_response(
        data=[PermissionResponse.model_validate(p) for p in items],
        meta={"pagination": meta.model_dump()},
    )


@router.post("/permissions", status_code=status.HTTP_201_CREATED)
async def create_permission(
    data: PermissionCreate,
    service: PermissionService = Depends(get_permission_service),
    _: User = Depends(require_permission("role:manage")),
) -> dict[str, Any]:
    permission = await service.create(data)
    return success_response(data=PermissionResponse.model_validate(permission))


@router.get("/roles")
async def list_roles(
    pagination: PaginationParams = Depends(get_pagination),
    service: RoleService = Depends(get_role_service),
    _: User = Depends(require_permission("role:manage")),
) -> dict[str, Any]:
    items, meta = await service.list_roles(pagination)
    return success_response(
        data=[RoleResponse.model_validate(r) for r in items],
        meta={"pagination": meta.model_dump()},
    )


@router.post("/roles", status_code=status.HTTP_201_CREATED)
async def create_role(
    data: RoleCreate,
    service: RoleService = Depends(get_role_service),
    _: User = Depends(require_permission("role:manage")),
) -> dict[str, Any]:
    role = await service.create(data)
    return success_response(data=RoleResponse.model_validate(role))


@router.get("/roles/{role_id}")
async def get_role(
    role_id: UUID,
    service: RoleService = Depends(get_role_service),
    _: User = Depends(require_permission("role:manage")),
) -> dict[str, Any]:
    role = await service.get(role_id)
    return success_response(data=RoleResponse.model_validate(role))


@router.patch("/roles/{role_id}")
async def update_role(
    role_id: UUID,
    data: RoleUpdate,
    service: RoleService = Depends(get_role_service),
    _: User = Depends(require_permission("role:manage")),
) -> dict[str, Any]:
    role = await service.update(role_id, data)
    return success_response(data=RoleResponse.model_validate(role))


@router.post("/roles/assign")
async def assign_role(
    data: UserRoleAssign,
    service: RoleService = Depends(get_role_service),
    _: User = Depends(require_permission("role:manage")),
) -> dict[str, Any]:
    assignment = await service.assign_role(data)
    return success_response(data=UserRoleResponse.model_validate(assignment))


@router.post("/roles/remove")
async def remove_role(
    data: UserRoleRemove,
    service: RoleService = Depends(get_role_service),
    _: User = Depends(require_permission("role:manage")),
) -> dict[str, Any]:
    await service.remove_role(data)
    return success_response(message="Role removed successfully.")


@router.delete("/permissions/{permission_id}")
async def delete_permission(
    permission_id: UUID,
    service: PermissionService = Depends(get_permission_service),
    _: User = Depends(require_permission("role:manage")),
) -> dict[str, Any]:
    await service.delete(permission_id)
    return success_response(message="Permission deleted successfully.")


@router.delete("/roles/{role_id}")
async def delete_role(
    role_id: UUID,
    service: RoleService = Depends(get_role_service),
    _: User = Depends(require_permission("role:manage")),
) -> dict[str, Any]:
    await service.delete(role_id)
    return success_response(message="Role deleted successfully.")


@router.get("/users/me/permissions")
async def list_my_permissions(
    current_user: User = Depends(get_current_active_user),
    service: AuthorizationService = Depends(get_authorization_service),
) -> dict[str, Any]:
    permissions = await service.get_user_permissions(current_user.id)
    return success_response(data=sorted(permissions))
