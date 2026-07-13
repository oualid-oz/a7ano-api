from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.auth.dependencies import get_current_active_user
from app.common.dependencies import get_pagination
from app.common.responses import success_response
from app.common.schemas import PaginationParams
from app.organizations.dependencies import (
    get_organization,
    get_organization_service,
    require_organization_permission,
)
from app.organizations.models import Organization
from app.organizations.schemas import (
    InvitationAccept,
    InvitationCreate,
    InvitationResponse,
    MemberRoleUpdate,
    OrganizationCreate,
    OrganizationResponse,
    OrganizationUpdate,
)
from app.organizations.service import OrganizationService
from app.permissions.dependencies import get_authorization_service
from app.permissions.service import AuthorizationService
from app.users.models import User

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_organization(
    data: OrganizationCreate,
    current_user: User = Depends(get_current_active_user),
    service: OrganizationService = Depends(get_organization_service),
) -> dict[str, Any]:
    organization = await service.create(data, current_user)
    return success_response(
        data=OrganizationResponse.model_validate(organization),
        message="Organization created successfully.",
    )


@router.get("")
async def list_organizations(
    pagination: PaginationParams = Depends(get_pagination),
    service: OrganizationService = Depends(get_organization_service),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    items, meta = await service.list_organizations(pagination, current_user)
    return success_response(
        data=[OrganizationResponse.model_validate(o) for o in items],
        meta={"pagination": meta.model_dump()},
    )


@router.get("/{org_id}")
async def get_organization_by_id(
    organization: Organization = Depends(get_organization),
    _: User = Depends(require_organization_permission("organization:read")),
) -> dict[str, Any]:
    return success_response(data=OrganizationResponse.model_validate(organization))


@router.patch("/{org_id}")
async def update_organization(
    org_id: UUID,
    data: OrganizationUpdate,
    current_user: User = Depends(get_current_active_user),
    _: User = Depends(require_organization_permission("organization:update")),
    service: OrganizationService = Depends(get_organization_service),
) -> dict[str, Any]:
    organization = await service.update(org_id, data, current_user)
    return success_response(
        data=OrganizationResponse.model_validate(organization),
        message="Organization updated successfully.",
    )


@router.delete("/{org_id}")
async def delete_organization(
    org_id: UUID,
    current_user: User = Depends(get_current_active_user),
    _: User = Depends(require_organization_permission("organization:delete")),
    service: OrganizationService = Depends(get_organization_service),
) -> dict[str, Any]:
    await service.delete(org_id, current_user)
    return success_response(message="Organization deleted successfully.")


@router.post("/{org_id}/invite")
async def invite_member(
    org_id: UUID,
    data: InvitationCreate,
    current_user: User = Depends(get_current_active_user),
    _: User = Depends(require_organization_permission("user:manage")),
    service: OrganizationService = Depends(get_organization_service),
) -> dict[str, Any]:
    invitation = await service.invite(org_id, data, current_user)
    return success_response(
        data=InvitationResponse.model_validate(invitation),
        message="Invitation sent successfully.",
    )


@router.post("/invitations/accept")
async def accept_invitation(
    data: InvitationAccept,
    current_user: User = Depends(get_current_active_user),
    service: OrganizationService = Depends(get_organization_service),
) -> dict[str, Any]:
    organization = await service.accept_invitation(data, current_user)
    return success_response(
        data=OrganizationResponse.model_validate(organization),
        message="Invitation accepted successfully.",
    )


@router.post("/invitations/{token}/revoke")
async def revoke_invitation(
    token: str,
    current_user: User = Depends(get_current_active_user),
    auth_service: AuthorizationService = Depends(get_authorization_service),
    service: OrganizationService = Depends(get_organization_service),
) -> dict[str, Any]:
    invitation = await service.get_invitation_by_token(token)
    if invitation is None:
        from app.organizations.exceptions import InvitationNotFoundException

        raise InvitationNotFoundException()
    if not await auth_service.has_permission(
        current_user.id, "user:manage", organization_id=invitation.organization_id
    ):
        from app.core.exceptions import AuthorizationException

        raise AuthorizationException()
    invitation = await service.revoke_invitation(token, current_user)
    return success_response(
        data=InvitationResponse.model_validate(invitation),
        message="Invitation revoked successfully.",
    )


@router.get("/{org_id}/members")
async def list_members(
    org_id: UUID,
    _: User = Depends(require_organization_permission("organization:read")),
    service: OrganizationService = Depends(get_organization_service),
) -> dict[str, Any]:
    members = await service.list_members(org_id)
    return success_response(data=members)


@router.patch("/{org_id}/members/{user_id}/role")
async def update_member_role(
    org_id: UUID,
    user_id: UUID,
    data: MemberRoleUpdate,
    current_user: User = Depends(get_current_active_user),
    _: User = Depends(require_organization_permission("user:manage")),
    service: OrganizationService = Depends(get_organization_service),
) -> dict[str, Any]:
    member = await service.update_member_role(org_id, user_id, data.role_id, current_user)
    return success_response(
        data=member,
        message="Member role updated successfully.",
    )


@router.delete("/{org_id}/members/{user_id}")
async def remove_member(
    org_id: UUID,
    user_id: UUID,
    current_user: User = Depends(get_current_active_user),
    _: User = Depends(require_organization_permission("user:manage")),
    service: OrganizationService = Depends(get_organization_service),
) -> dict[str, Any]:
    await service.remove_member(org_id, user_id, current_user)
    return success_response(message="Member removed successfully.")


@router.get("/{org_id}/invitations")
async def list_invitations(
    org_id: UUID,
    _: User = Depends(require_organization_permission("user:manage")),
    service: OrganizationService = Depends(get_organization_service),
) -> dict[str, Any]:
    invitations = await service.list_invitations(org_id)
    return success_response(data=[InvitationResponse.model_validate(i) for i in invitations])
