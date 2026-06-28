"""Unit tests for TeamService — no database required."""
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.core.exceptions import DuplicateValueException
from app.organizations.exceptions import OrganizationNotFoundException
from app.teams.exceptions import TeamMemberNotFoundException, TeamNotFoundException
from app.teams.schemas import TeamCreate, TeamMemberAdd, TeamMemberRemove, TeamUpdate
from app.teams.service import TeamService

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_user(user_id=None, email="user@example.com"):
    user = MagicMock()
    user.id = user_id or uuid4()
    user.email = email
    user.full_name = "Test User"
    user.deleted_at = None
    return user


def _make_org(org_id=None):
    org = MagicMock()
    org.id = org_id or uuid4()
    org.name = "Test Org"
    return org


def _make_team(team_id=None, org_id=None):
    team = MagicMock()
    team.id = team_id or uuid4()
    team.organization_id = org_id or uuid4()
    team.name = "Test Team"
    team.description = None
    team.deleted_at = None
    return team


def _make_role(role_id=None, name="team_admin"):
    role = MagicMock()
    role.id = role_id or uuid4()
    role.name = name
    return role


def _make_user_role(user_id=None, role_id=None, team_id=None, org_id=None):
    ur = MagicMock()
    ur.id = uuid4()
    ur.user_id = user_id or uuid4()
    ur.role_id = role_id or uuid4()
    ur.team_id = team_id or uuid4()
    ur.organization_id = org_id or uuid4()
    ur.role = _make_role()
    return ur


# ── TestTeamService ───────────────────────────────────────────────────────────


@pytest.mark.anyio
class TestTeamService:
    def _make_service(
        self,
        team_repo=None,
        org_repo=None,
        role_repo=None,
        user_role_repo=None,
        user_repo=None,
    ) -> TeamService:
        return TeamService(
            team_repository=team_repo or AsyncMock(),
            organization_repository=org_repo or AsyncMock(),
            role_repository=role_repo or AsyncMock(),
            user_role_repository=user_role_repo or AsyncMock(),
            user_repository=user_repo or AsyncMock(),
        )

    async def test_create_team_success(self):
        user = _make_user()
        org = _make_org()
        team = _make_team(org_id=org.id)
        role = _make_role(name="team_admin")

        org_repo = AsyncMock()
        org_repo.get_active_by_id.return_value = org

        team_repo = AsyncMock()
        team_repo.create.return_value = team

        role_repo = AsyncMock()
        role_repo.get_by_name.return_value = role

        user_role_repo = AsyncMock()

        service = self._make_service(
            team_repo=team_repo,
            org_repo=org_repo,
            role_repo=role_repo,
            user_role_repo=user_role_repo,
        )
        data = TeamCreate(name="Engineering")
        result = await service.create(org.id, data, user)

        assert result is team
        team_repo.create.assert_awaited_once()
        user_role_repo.create.assert_awaited_once()

    async def test_create_team_org_not_found(self):
        user = _make_user()
        org_repo = AsyncMock()
        org_repo.get_active_by_id.return_value = None

        service = self._make_service(org_repo=org_repo)
        data = TeamCreate(name="Engineering")

        with pytest.raises(OrganizationNotFoundException):
            await service.create(uuid4(), data, user)

    async def test_get_team_found(self):
        team = _make_team()
        team_repo = AsyncMock()
        team_repo.get_active_by_id.return_value = team

        service = self._make_service(team_repo=team_repo)
        result = await service.get(team.id)

        assert result is team

    async def test_get_team_not_found(self):
        team_repo = AsyncMock()
        team_repo.get_active_by_id.return_value = None

        service = self._make_service(team_repo=team_repo)
        with pytest.raises(TeamNotFoundException):
            await service.get(uuid4())

    async def test_update_team_success(self):
        user = _make_user()
        team = _make_team()
        updated = _make_team(team_id=team.id)
        updated.name = "Backend"

        team_repo = AsyncMock()
        team_repo.get_active_by_id.return_value = team
        team_repo.update.return_value = updated

        service = self._make_service(team_repo=team_repo)
        data = TeamUpdate(name="Backend")
        result = await service.update(team.id, data, user)

        assert result is updated
        team_repo.update.assert_awaited_once()

    async def test_delete_team_success(self):
        user = _make_user()
        team = _make_team()

        team_repo = AsyncMock()
        team_repo.get_active_by_id.return_value = team
        team_repo.delete_soft.return_value = team

        service = self._make_service(team_repo=team_repo)
        result = await service.delete(team.id, user)

        assert result is team
        team_repo.delete_soft.assert_awaited_once_with(team)

    async def test_add_member_success(self):
        user = _make_user()
        team = _make_team()
        role = _make_role()
        membership = _make_user_role(user_id=user.id, role_id=role.id, team_id=team.id)

        team_repo = AsyncMock()
        team_repo.get_active_by_id.return_value = team

        role_repo = AsyncMock()
        role_repo.get_or_404.return_value = role

        user_role_repo = AsyncMock()
        user_role_repo.get_assignment.return_value = None
        user_role_repo.create.return_value = membership

        service = self._make_service(
            team_repo=team_repo, role_repo=role_repo, user_role_repo=user_role_repo
        )
        data = TeamMemberAdd(user_id=user.id, role_id=role.id)
        result = await service.add_member(team.id, data, user)

        assert result is membership
        user_role_repo.create.assert_awaited_once()

    async def test_add_member_already_exists(self):
        user = _make_user()
        team = _make_team()
        role = _make_role()
        existing = _make_user_role()

        team_repo = AsyncMock()
        team_repo.get_active_by_id.return_value = team

        role_repo = AsyncMock()
        role_repo.get_or_404.return_value = role

        user_role_repo = AsyncMock()
        user_role_repo.get_assignment.return_value = existing

        service = self._make_service(
            team_repo=team_repo, role_repo=role_repo, user_role_repo=user_role_repo
        )
        data = TeamMemberAdd(user_id=user.id, role_id=role.id)

        with pytest.raises(DuplicateValueException):
            await service.add_member(team.id, data, user)

    async def test_remove_member_success(self):
        user = _make_user()
        team = _make_team()
        assignment = _make_user_role(user_id=user.id, team_id=team.id)

        team_repo = AsyncMock()
        team_repo.get_active_by_id.return_value = team

        user_role_repo = AsyncMock()
        user_role_repo.get_assignment.return_value = assignment

        service = self._make_service(team_repo=team_repo, user_role_repo=user_role_repo)
        data = TeamMemberRemove(user_id=user.id, role_id=assignment.role_id)
        await service.remove_member(team.id, data, user)

        user_role_repo.delete_soft.assert_awaited_once_with(assignment)

    async def test_remove_member_not_found(self):
        user = _make_user()
        team = _make_team()

        team_repo = AsyncMock()
        team_repo.get_active_by_id.return_value = team

        user_role_repo = AsyncMock()
        user_role_repo.get_assignment.return_value = None

        service = self._make_service(team_repo=team_repo, user_role_repo=user_role_repo)
        data = TeamMemberRemove(user_id=user.id, role_id=uuid4())

        with pytest.raises(TeamMemberNotFoundException):
            await service.remove_member(team.id, data, user)

    async def test_list_members_skips_deleted_users(self):
        team = _make_team()
        active_user = _make_user(email="active@example.com")
        active_user.deleted_at = None

        deleted_user = _make_user(email="deleted@example.com")
        deleted_user.deleted_at = datetime.now(UTC)

        a1 = _make_user_role(user_id=active_user.id, team_id=team.id)
        a1.user_id = active_user.id
        a1.role.name = "member"

        a2 = _make_user_role(user_id=deleted_user.id, team_id=team.id)
        a2.user_id = deleted_user.id
        a2.role.name = "member"

        team_repo = AsyncMock()
        team_repo.get_active_by_id.return_value = team

        user_role_repo = AsyncMock()
        user_role_repo.list_by_team.return_value = [a1, a2]

        user_repo = AsyncMock()
        user_repo.get.side_effect = [active_user, deleted_user]

        service = self._make_service(
            team_repo=team_repo, user_role_repo=user_role_repo, user_repo=user_repo
        )
        members = await service.list_members(team.id)

        assert len(members) == 1
        assert members[0].email == active_user.email
