"""Unit tests for OrganizationService — no database required."""
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.organizations.exceptions import (
    InvitationAlreadyProcessedException,
    InvitationExpiredException,
    OrganizationNotFoundException,
    OrganizationSlugExistsException,
)
from app.organizations.schemas import (
    InvitationAccept,
    InvitationCreate,
    OrganizationCreate,
    OrganizationUpdate,
)
from app.organizations.service import OrganizationService

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_user(user_id=None, email="user@example.com"):
    user = MagicMock()
    user.id = user_id or uuid4()
    user.email = email
    user.full_name = "Test User"
    user.deleted_at = None
    return user


def _make_org(org_id=None, slug="test-org"):
    org = MagicMock()
    org.id = org_id or uuid4()
    org.name = "Test Org"
    org.slug = slug
    org.deleted_at = None
    return org


def _make_role(role_id=None, name="organization_admin"):
    role = MagicMock()
    role.id = role_id or uuid4()
    role.name = name
    return role


def _make_invitation(
    email="invitee@example.com",
    status="pending",
    expired=False,
    org_id=None,
    role_id=None,
):
    inv = MagicMock()
    inv.id = uuid4()
    inv.email = email
    inv.token = "valid-token-abc"
    inv.organization_id = org_id or uuid4()
    inv.role_id = role_id or uuid4()
    inv.status = status
    inv.is_expired.return_value = expired
    return inv


# ── TestOrganizationService ───────────────────────────────────────────────────


@pytest.mark.anyio
class TestOrganizationService:
    def _make_service(
        self,
        org_repo=None,
        inv_repo=None,
        role_repo=None,
        user_role_repo=None,
        user_repo=None,
    ) -> OrganizationService:
        return OrganizationService(
            organization_repository=org_repo or AsyncMock(),
            invitation_repository=inv_repo or AsyncMock(),
            role_repository=role_repo or AsyncMock(),
            user_role_repository=user_role_repo or AsyncMock(),
            user_repository=user_repo or AsyncMock(),
        )

    async def test_create_org_success(self):
        user = _make_user()
        org = _make_org()
        role = _make_role()

        org_repo = AsyncMock()
        org_repo.get_by_slug.return_value = None
        org_repo.create.return_value = org

        role_repo = AsyncMock()
        role_repo.get_by_name.return_value = role

        user_role_repo = AsyncMock()

        service = self._make_service(
            org_repo=org_repo, role_repo=role_repo, user_role_repo=user_role_repo
        )
        data = OrganizationCreate(name="Test Org", slug="test-org")
        result = await service.create(data, user)

        assert result is org
        org_repo.create.assert_awaited_once()
        user_role_repo.create.assert_awaited_once()

    async def test_create_org_slug_exists(self):
        user = _make_user()
        org_repo = AsyncMock()
        org_repo.get_by_slug.return_value = _make_org()

        service = self._make_service(org_repo=org_repo)
        data = OrganizationCreate(name="Test Org", slug="existing-slug")

        with pytest.raises(OrganizationSlugExistsException):
            await service.create(data, user)

    async def test_get_org_found(self):
        org = _make_org()
        org_repo = AsyncMock()
        org_repo.get_active_by_id.return_value = org

        service = self._make_service(org_repo=org_repo)
        result = await service.get(org.id)

        assert result is org

    async def test_get_org_not_found(self):
        org_repo = AsyncMock()
        org_repo.get_active_by_id.return_value = None

        service = self._make_service(org_repo=org_repo)
        with pytest.raises(OrganizationNotFoundException):
            await service.get(uuid4())

    async def test_update_org_success(self):
        user = _make_user()
        org = _make_org()
        updated_org = _make_org(org_id=org.id)
        updated_org.name = "Updated Org"

        org_repo = AsyncMock()
        org_repo.get_active_by_id.return_value = org
        org_repo.update.return_value = updated_org

        service = self._make_service(org_repo=org_repo)
        data = OrganizationUpdate(name="Updated Org")
        result = await service.update(org.id, data, user)

        assert result is updated_org
        org_repo.update.assert_awaited_once()

    async def test_invite_member_success(self):
        user = _make_user()
        org = _make_org()
        role = _make_role()
        invitation = _make_invitation(email="invitee@example.com")

        org_repo = AsyncMock()
        org_repo.get_active_by_id.return_value = org

        role_repo = AsyncMock()
        role_repo.get_or_404.return_value = role

        inv_repo = AsyncMock()
        inv_repo.create.return_value = invitation

        service = self._make_service(
            org_repo=org_repo, inv_repo=inv_repo, role_repo=role_repo
        )
        data = InvitationCreate(email="invitee@example.com", role_id=role.id)
        result = await service.invite(org.id, data, user)

        assert result is invitation
        inv_repo.create.assert_awaited_once()
        created_inv = inv_repo.create.call_args[0][0]
        assert created_inv.token  # token was generated

    async def test_accept_invitation_success(self):
        user = _make_user(email="invitee@example.com")
        org = _make_org()
        invitation = _make_invitation(
            email=user.email, status="pending", expired=False, org_id=org.id
        )

        inv_repo = AsyncMock()
        inv_repo.get_by_token.return_value = invitation
        inv_repo.update.return_value = invitation

        org_repo = AsyncMock()
        org_repo.get_active_by_id.return_value = org

        user_role_repo = AsyncMock()
        user_role_repo.get_assignment.return_value = None

        service = self._make_service(
            org_repo=org_repo, inv_repo=inv_repo, user_role_repo=user_role_repo
        )
        data = InvitationAccept(token="valid-token-abc")
        result = await service.accept_invitation(data, user)

        assert result is org
        user_role_repo.create.assert_awaited_once()
        invitation.accept.assert_called_once_with(user.id)

    async def test_accept_invitation_expired(self):
        user = _make_user(email="invitee@example.com")
        invitation = _make_invitation(email=user.email, status="pending", expired=True)

        inv_repo = AsyncMock()
        inv_repo.get_by_token.return_value = invitation

        service = self._make_service(inv_repo=inv_repo)
        data = InvitationAccept(token="valid-token-abc")

        with pytest.raises(InvitationExpiredException):
            await service.accept_invitation(data, user)

    async def test_accept_invitation_already_processed(self):
        user = _make_user(email="invitee@example.com")
        invitation = _make_invitation(email=user.email, status="accepted", expired=False)

        inv_repo = AsyncMock()
        inv_repo.get_by_token.return_value = invitation

        service = self._make_service(inv_repo=inv_repo)
        data = InvitationAccept(token="valid-token-abc")

        with pytest.raises(InvitationAlreadyProcessedException):
            await service.accept_invitation(data, user)

    async def test_revoke_invitation_success(self):
        user = _make_user()
        invitation = _make_invitation(status="pending")
        revoked = _make_invitation(status="revoked")

        inv_repo = AsyncMock()
        inv_repo.get_by_token.return_value = invitation
        inv_repo.update.return_value = revoked

        service = self._make_service(inv_repo=inv_repo)
        result = await service.revoke_invitation("valid-token-abc", user)

        assert result is revoked
        invitation.revoke.assert_called_once()

    async def test_list_members_skips_deleted_users(self):
        from datetime import UTC, datetime

        org = _make_org()
        active_user = _make_user(email="active@example.com")
        active_user.deleted_at = None

        deleted_user = _make_user(email="deleted@example.com")
        deleted_user.deleted_at = datetime.now(UTC)

        active_assignment = MagicMock()
        active_assignment.user_id = active_user.id
        active_assignment.role_id = uuid4()
        active_assignment.role = MagicMock(name="member")
        active_assignment.role.name = "member"

        deleted_assignment = MagicMock()
        deleted_assignment.user_id = deleted_user.id
        deleted_assignment.role_id = uuid4()
        deleted_assignment.role = MagicMock(name="member")
        deleted_assignment.role.name = "member"

        org_repo = AsyncMock()
        org_repo.get_active_by_id.return_value = org

        user_role_repo = AsyncMock()
        user_role_repo.list_by_organization.return_value = [
            active_assignment,
            deleted_assignment,
        ]

        user_repo = AsyncMock()
        user_repo.get.side_effect = [active_user, deleted_user]

        service = self._make_service(
            org_repo=org_repo, user_role_repo=user_role_repo, user_repo=user_repo
        )
        members = await service.list_members(org.id)

        assert len(members) == 1
        assert members[0].email == active_user.email
