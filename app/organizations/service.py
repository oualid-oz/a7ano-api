from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe
from uuid import UUID, uuid4

from app.common.schemas import PaginationMeta, PaginationParams
from app.organizations.exceptions import (
    InvitationAlreadyProcessedException,
    InvitationExpiredException,
    InvitationNotFoundException,
    OrganizationNotFoundException,
    OrganizationSlugExistsException,
)
from app.organizations.models import Organization, OrganizationInvitation
from app.organizations.repository import (
    InvitationRepository,
    OrganizationRepository,
)
from app.organizations.schemas import (
    InvitationAccept,
    InvitationCreate,
    MemberResponse,
    OrganizationCreate,
    OrganizationUpdate,
)
from app.permissions.models import UserRole
from app.permissions.repository import RoleRepository, UserRoleRepository
from app.users.models import User
from app.users.repository import UserRepository


async def _generate_unique_slug(name: str, exists: Callable[[str], Awaitable[bool]]) -> str:
    import re

    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if not base:
        base = "org"
    slug = base[:120]
    if not await exists(slug):
        return slug
    suffix = uuid4().hex[:8]
    return f"{slug}-{suffix}"


class OrganizationService:
    def __init__(
        self,
        organization_repository: OrganizationRepository,
        invitation_repository: InvitationRepository,
        role_repository: RoleRepository,
        user_role_repository: UserRoleRepository,
        user_repository: UserRepository,
    ) -> None:
        self._organization_repository = organization_repository
        self._invitation_repository = invitation_repository
        self._role_repository = role_repository
        self._user_role_repository = user_role_repository
        self._user_repository = user_repository

    async def create(self, data: OrganizationCreate, current_user: User) -> Organization:
        slug = data.slug or await _generate_unique_slug(data.name, self._slug_exists)
        existing = await self._organization_repository.get_by_slug(slug)
        if existing is not None:
            raise OrganizationSlugExistsException()

        organization = Organization(
            name=data.name,
            slug=slug,
            description=data.description,
            logo_url=data.logo_url,
            owner_id=current_user.id,
            created_by=current_user.id,
            updated_by=current_user.id,
        )
        organization = await self._organization_repository.create(organization)
        await self._assign_owner_role(organization, current_user)
        return organization

    async def get(self, org_id: UUID) -> Organization:
        organization = await self._organization_repository.get_active_by_id(org_id)
        if organization is None:
            raise OrganizationNotFoundException()
        return organization

    async def update(
        self, org_id: UUID, data: OrganizationUpdate, current_user: User
    ) -> Organization:
        organization = await self.get(org_id)
        update_data = data.model_dump(exclude_unset=True)
        update_data["updated_by"] = current_user.id
        return await self._organization_repository.update(organization, update_data)

    async def delete(self, org_id: UUID, current_user: User) -> Organization:
        organization = await self.get(org_id)
        organization.updated_by = current_user.id
        return await self._organization_repository.delete_soft(organization)

    async def list_organizations(
        self, pagination: PaginationParams
    ) -> tuple[list[Organization], PaginationMeta]:
        return await self._organization_repository.list(pagination)

    async def invite(
        self,
        org_id: UUID,
        data: InvitationCreate,
        current_user: User,
    ) -> OrganizationInvitation:
        organization = await self.get(org_id)
        role = await self._role_repository.get_or_404(data.role_id)
        token = token_urlsafe(32)
        invitation = OrganizationInvitation(
            email=str(data.email),
            token=token,
            organization_id=organization.id,
            invited_by_id=current_user.id,
            role_id=role.id,
            expires_at=datetime.now(UTC) + timedelta(days=7),
            created_by=current_user.id,
            updated_by=current_user.id,
        )
        return await self._invitation_repository.create(invitation)

    async def accept_invitation(self, data: InvitationAccept, current_user: User) -> Organization:
        invitation = await self._invitation_repository.get_by_token(data.token)
        if invitation is None:
            raise InvitationNotFoundException()
        if invitation.status != "pending":
            raise InvitationAlreadyProcessedException()
        if invitation.is_expired():
            raise InvitationExpiredException()
        if invitation.email != current_user.email:
            raise InvitationNotFoundException()

        invitation.accept(current_user.id)
        await self._invitation_repository.update(invitation, {})

        existing = await self._user_role_repository.get_assignment(
            current_user.id,
            invitation.role_id,
            invitation.organization_id,
            None,
        )
        if existing is None:
            membership = UserRole(
                user_id=current_user.id,
                role_id=invitation.role_id,
                organization_id=invitation.organization_id,
            )
            await self._user_role_repository.create(membership)

        return await self.get(invitation.organization_id)

    async def get_invitation_by_token(self, token: str) -> OrganizationInvitation | None:
        return await self._invitation_repository.get_by_token(token)

    async def revoke_invitation(self, token: str, current_user: User) -> OrganizationInvitation:
        invitation = await self._invitation_repository.get_by_token(token)
        if invitation is None:
            raise InvitationNotFoundException()
        if invitation.status != "pending":
            raise InvitationAlreadyProcessedException()
        invitation.revoke()
        invitation.updated_by = current_user.id
        return await self._invitation_repository.update(invitation, {})

    async def list_members(self, org_id: UUID) -> list[MemberResponse]:
        await self.get(org_id)
        assignments = await self._user_role_repository.list_by_organization(org_id)
        members: list[MemberResponse] = []
        for assignment in assignments:
            user = await self._user_repository.get(assignment.user_id)
            if user is None or user.deleted_at is not None:
                continue
            members.append(
                MemberResponse(
                    user_id=user.id,
                    full_name=user.full_name,
                    email=user.email,
                    role_id=assignment.role_id,
                    role_name=assignment.role.name,
                )
            )
        return members

    async def list_invitations(self, org_id: UUID) -> list[OrganizationInvitation]:
        await self.get(org_id)
        return await self._invitation_repository.list_by_organization(org_id)

    async def _slug_exists(self, slug: str) -> bool:
        existing = await self._organization_repository.get_by_slug(slug)
        return existing is not None

    async def _assign_owner_role(self, organization: Organization, owner: User) -> None:
        role = await self._role_repository.get_by_name("organization_admin")
        if role is None:
            role = await self._role_repository.get_by_name("super_admin")
        if role is None:
            return
        membership = UserRole(
            user_id=owner.id,
            role_id=role.id,
            organization_id=organization.id,
        )
        await self._user_role_repository.create(membership)
