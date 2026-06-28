from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends

from app.audit.dependencies import get_audit_service
from app.audit.schemas import AuditEventResponse
from app.audit.service import AuditService
from app.auth.dependencies import get_current_active_user
from app.common.dependencies import get_pagination
from app.common.responses import success_response
from app.common.schemas import PaginationParams
from app.organizations.dependencies import require_organization_permission
from app.permissions.dependencies import require_role
from app.users.models import User

router = APIRouter(tags=["audit"])


@router.get("/organizations/{org_id}/audit-events")
async def list_organization_audit_events(
    org_id: UUID,
    pagination: PaginationParams = Depends(get_pagination),
    _: User = Depends(require_organization_permission("organization:read")),
    service: AuditService = Depends(get_audit_service),
) -> dict[str, Any]:
    items, meta = await service.list_by_organization(org_id, pagination)
    return success_response(
        data=[AuditEventResponse.model_validate(e) for e in items],
        meta={"pagination": meta.model_dump()},
    )


@router.get("/audit-events/me")
async def list_my_audit_events(
    pagination: PaginationParams = Depends(get_pagination),
    current_user: User = Depends(get_current_active_user),
    service: AuditService = Depends(get_audit_service),
) -> dict[str, Any]:
    items, meta = await service.list_by_actor(current_user.id, pagination)
    return success_response(
        data=[AuditEventResponse.model_validate(e) for e in items],
        meta={"pagination": meta.model_dump()},
    )


@router.get("/audit-events/resource/{resource_type}/{resource_id}")
async def list_resource_audit_events(
    resource_type: str,
    resource_id: str,
    pagination: PaginationParams = Depends(get_pagination),
    _: User = Depends(require_role("super_admin")),
    service: AuditService = Depends(get_audit_service),
) -> dict[str, Any]:
    items, meta = await service.list_by_resource(resource_type, resource_id, pagination)
    return success_response(
        data=[AuditEventResponse.model_validate(e) for e in items],
        meta={"pagination": meta.model_dump()},
    )
