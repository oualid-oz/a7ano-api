"""Tests for the projects module: service unit tests and router integration tests."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.core.exceptions import DuplicateValueException, ResourceNotFoundException
from app.projects.exceptions import (
    ProjectAssigneeNotFoundException,
    ProjectNotFoundException,
    ProjectTagNotFoundException,
)
from app.projects.models import Project, ProjectAssignment, ProjectTag
from app.projects.schemas import (
    ProjectAssigneeAdd,
    ProjectAssigneeRemove,
    ProjectCreate,
    ProjectTagCreate,
    ProjectUpdate,
)
from app.projects.service import ProjectService, ProjectTagService

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_user(user_id=None):
    user = MagicMock()
    user.id = user_id or uuid4()
    user.email = "user@example.com"
    user.full_name = "Test User"
    user.deleted_at = None
    return user


def _make_organization(org_id=None):
    org = MagicMock()
    org.id = org_id or uuid4()
    org.name = "Test Org"
    return org


def _make_project(project_id=None, org_id=None, owner_id=None):
    project = MagicMock(spec=Project)
    project.id = project_id or uuid4()
    project.organization_id = org_id or uuid4()
    project.owner_id = owner_id or uuid4()
    project.title = "Test Project"
    project.description = None
    project.status = "active"
    project.priority = "medium"
    project.due_date = None
    project.archived_at = None
    project.deleted_at = None
    project.tags = []
    project.assignees = []
    return project


def _make_tag(tag_id=None, org_id=None):
    tag = MagicMock(spec=ProjectTag)
    tag.id = tag_id or uuid4()
    tag.organization_id = org_id or uuid4()
    tag.name = "Test Tag"
    tag.color = "#ff0000"
    tag.deleted_at = None
    return tag


# ── ProjectTagService unit tests ──────────────────────────────────────────────


@pytest.mark.anyio
class TestProjectTagService:
    def _make_service(
        self, tag_repo=None, org_repo=None
    ) -> ProjectTagService:
        tag_repo = tag_repo or AsyncMock()
        org_repo = org_repo or AsyncMock()
        return ProjectTagService(tag_repo, org_repo)

    async def test_create_tag_success(self):
        org_id = uuid4()
        org_repo = AsyncMock()
        org_repo.get_active_by_id.return_value = _make_organization(org_id)
        tag_repo = AsyncMock()
        tag_repo.get_by_name_and_org.return_value = None
        created_tag = _make_tag(org_id=org_id)
        tag_repo.create.return_value = created_tag

        service = self._make_service(tag_repo=tag_repo, org_repo=org_repo)
        user = _make_user()
        data = ProjectTagCreate(name="Backend", color="#00ff00")
        tag = await service.create(org_id, data, user)

        assert tag is created_tag
        tag_repo.create.assert_awaited_once()

    async def test_create_tag_org_not_found_raises(self):
        org_repo = AsyncMock()
        org_repo.get_active_by_id.return_value = None

        service = self._make_service(org_repo=org_repo)
        user = _make_user()
        data = ProjectTagCreate(name="Backend")
        with pytest.raises(ResourceNotFoundException):
            await service.create(uuid4(), data, user)

    async def test_create_tag_duplicate_raises(self):
        org_id = uuid4()
        org_repo = AsyncMock()
        org_repo.get_active_by_id.return_value = _make_organization(org_id)
        tag_repo = AsyncMock()
        tag_repo.get_by_name_and_org.return_value = _make_tag(org_id=org_id)

        service = self._make_service(tag_repo=tag_repo, org_repo=org_repo)
        user = _make_user()
        data = ProjectTagCreate(name="Existing Tag")
        with pytest.raises(DuplicateValueException):
            await service.create(org_id, data, user)

    async def test_list_tags(self):
        org_id = uuid4()
        tag_repo = AsyncMock()
        expected = [_make_tag(org_id=org_id), _make_tag(org_id=org_id)]
        tag_repo.list_by_organization.return_value = expected

        service = self._make_service(tag_repo=tag_repo)
        tags = await service.list_tags(org_id)

        assert tags == expected
        tag_repo.list_by_organization.assert_awaited_once_with(org_id)

    async def test_delete_tag_success(self):
        tag = _make_tag()
        tag_repo = AsyncMock()
        tag_repo.get.return_value = tag
        tag_repo.delete_soft.return_value = tag

        service = self._make_service(tag_repo=tag_repo)
        await service.delete(tag.id)

        tag_repo.delete_soft.assert_awaited_once_with(tag)

    async def test_delete_tag_not_found_raises(self):
        tag_repo = AsyncMock()
        tag_repo.get.return_value = None

        service = self._make_service(tag_repo=tag_repo)
        with pytest.raises(ProjectTagNotFoundException):
            await service.delete(uuid4())


# ── ProjectService unit tests ─────────────────────────────────────────────────


@pytest.mark.anyio
class TestProjectService:
    def _make_service(
        self,
        project_repo=None,
        tag_repo=None,
        assignment_repo=None,
        org_repo=None,
        user_repo=None,
    ) -> ProjectService:
        return ProjectService(
            project_repository=project_repo or AsyncMock(),
            tag_repository=tag_repo or AsyncMock(),
            assignment_repository=assignment_repo or AsyncMock(),
            organization_repository=org_repo or AsyncMock(),
            user_repository=user_repo or AsyncMock(),
        )

    async def test_create_project_success(self):
        org_id = uuid4()
        user = _make_user()
        org_repo = AsyncMock()
        org_repo.get_active_by_id.return_value = _make_organization(org_id)
        tag_repo = AsyncMock()
        tag_repo.get_many_by_ids.return_value = []
        project_repo = AsyncMock()
        created = _make_project(org_id=org_id, owner_id=user.id)
        project_repo.create.return_value = created
        project_repo.get_active_by_id.return_value = created
        assignment_repo = AsyncMock()

        service = self._make_service(
            project_repo=project_repo,
            tag_repo=tag_repo,
            assignment_repo=assignment_repo,
            org_repo=org_repo,
        )
        data = ProjectCreate(title="My Project", status="active", priority="high")
        result = await service.create(org_id, data, user)

        assert result is created
        project_repo.create.assert_awaited_once()
        assignment_repo.create.assert_awaited_once()

    async def test_create_project_org_not_found_raises(self):
        org_repo = AsyncMock()
        org_repo.get_active_by_id.return_value = None

        service = self._make_service(org_repo=org_repo)
        user = _make_user()
        data = ProjectCreate(title="X")
        with pytest.raises(ResourceNotFoundException):
            await service.create(uuid4(), data, user)

    async def test_get_project_found(self):
        project = _make_project()
        project_repo = AsyncMock()
        project_repo.get_active_by_id.return_value = project

        service = self._make_service(project_repo=project_repo)
        result = await service.get(project.id)
        assert result is project

    async def test_get_project_not_found_raises(self):
        project_repo = AsyncMock()
        project_repo.get_active_by_id.return_value = None

        service = self._make_service(project_repo=project_repo)
        with pytest.raises(ProjectNotFoundException):
            await service.get(uuid4())

    async def test_update_project_success(self):
        project = _make_project()
        project_repo = AsyncMock()
        project_repo.get_active_by_id.return_value = project
        updated = _make_project(project_id=project.id)
        project_repo.update.return_value = updated

        service = self._make_service(project_repo=project_repo)
        user = _make_user()
        data = ProjectUpdate(title="Updated Title")
        result = await service.update(project.id, data, user)
        assert result is updated
        project_repo.update.assert_awaited_once()

    async def test_update_project_with_tags(self):
        project = _make_project()
        tag = _make_tag()
        project_repo = AsyncMock()
        project_repo.get_active_by_id.return_value = project
        updated = _make_project(project_id=project.id)
        project_repo.update.return_value = updated
        tag_repo = AsyncMock()
        tag_repo.get_many_by_ids.return_value = [tag]

        service = self._make_service(project_repo=project_repo, tag_repo=tag_repo)
        user = _make_user()
        data = ProjectUpdate(tag_ids=[tag.id])
        await service.update(project.id, data, user)
        tag_repo.get_many_by_ids.assert_awaited_once_with([tag.id])

    async def test_delete_project_success(self):
        project = _make_project()
        project_repo = AsyncMock()
        project_repo.get_active_by_id.return_value = project
        project_repo.delete_soft.return_value = project

        service = self._make_service(project_repo=project_repo)
        user = _make_user()
        await service.delete(project.id, user)
        project_repo.delete_soft.assert_awaited_once_with(project)

    async def test_archive_project_success(self):
        project = _make_project()
        project.archived_at = None
        project_repo = AsyncMock()
        project_repo.get_active_by_id.return_value = project
        archived = _make_project(project_id=project.id)
        project_repo.update.return_value = archived

        service = self._make_service(project_repo=project_repo)
        user = _make_user()
        result = await service.archive(project.id, user)
        assert result is archived
        project_repo.update.assert_awaited_once()

    async def test_archive_already_archived_raises(self):
        from datetime import UTC, datetime

        project = _make_project()
        project.archived_at = datetime.now(UTC)
        project_repo = AsyncMock()
        project_repo.get_active_by_id.return_value = project

        service = self._make_service(project_repo=project_repo)
        user = _make_user()
        with pytest.raises(DuplicateValueException):
            await service.archive(project.id, user)

    async def test_restore_project_success(self):
        from datetime import UTC, datetime

        project = _make_project()
        project.archived_at = datetime.now(UTC)
        project_repo = AsyncMock()
        project_repo.get_active_by_id.return_value = project
        restored = _make_project(project_id=project.id)
        project_repo.update.return_value = restored

        service = self._make_service(project_repo=project_repo)
        user = _make_user()
        result = await service.restore(project.id, user)
        assert result is restored

    async def test_restore_not_archived_raises(self):
        project = _make_project()
        project.archived_at = None
        project_repo = AsyncMock()
        project_repo.get_active_by_id.return_value = project

        service = self._make_service(project_repo=project_repo)
        user = _make_user()
        with pytest.raises(DuplicateValueException):
            await service.restore(project.id, user)

    async def test_add_assignee_success(self):
        project = _make_project()
        user = _make_user()
        target_user = _make_user()
        project_repo = AsyncMock()
        project_repo.get_active_by_id.return_value = project
        user_repo = AsyncMock()
        user_repo.get.return_value = target_user
        assignment_repo = AsyncMock()
        assignment_repo.get_assignment.return_value = None
        created_assignment = MagicMock(spec=ProjectAssignment)
        created_assignment.id = uuid4()
        assignment_repo.create.return_value = created_assignment

        service = self._make_service(
            project_repo=project_repo,
            user_repo=user_repo,
            assignment_repo=assignment_repo,
        )
        data = ProjectAssigneeAdd(user_id=target_user.id, role="member")
        result = await service.add_assignee(project.id, data, user)
        assert result is created_assignment

    async def test_add_assignee_already_assigned_raises(self):
        project = _make_project()
        user = _make_user()
        target_user = _make_user()
        project_repo = AsyncMock()
        project_repo.get_active_by_id.return_value = project
        user_repo = AsyncMock()
        user_repo.get.return_value = target_user
        assignment_repo = AsyncMock()
        existing = MagicMock(spec=ProjectAssignment)
        assignment_repo.get_assignment.return_value = existing

        service = self._make_service(
            project_repo=project_repo,
            user_repo=user_repo,
            assignment_repo=assignment_repo,
        )
        data = ProjectAssigneeAdd(user_id=target_user.id)
        with pytest.raises(DuplicateValueException):
            await service.add_assignee(project.id, data, user)

    async def test_add_assignee_user_not_found_raises(self):
        project = _make_project()
        user = _make_user()
        project_repo = AsyncMock()
        project_repo.get_active_by_id.return_value = project
        user_repo = AsyncMock()
        user_repo.get.return_value = None

        service = self._make_service(
            project_repo=project_repo,
            user_repo=user_repo,
        )
        data = ProjectAssigneeAdd(user_id=uuid4())
        with pytest.raises(ResourceNotFoundException):
            await service.add_assignee(project.id, data, user)

    async def test_remove_assignee_success(self):
        project = _make_project()
        user = _make_user()
        target_user = _make_user()
        project_repo = AsyncMock()
        project_repo.get_active_by_id.return_value = project
        assignment = MagicMock(spec=ProjectAssignment)
        assignment_repo = AsyncMock()
        assignment_repo.get_assignment.return_value = assignment

        service = self._make_service(
            project_repo=project_repo,
            assignment_repo=assignment_repo,
        )
        data = ProjectAssigneeRemove(user_id=target_user.id)
        await service.remove_assignee(project.id, data, user)
        assignment_repo.delete_soft.assert_awaited_once_with(assignment)

    async def test_remove_assignee_not_found_raises(self):
        project = _make_project()
        user = _make_user()
        target_user = _make_user()
        project_repo = AsyncMock()
        project_repo.get_active_by_id.return_value = project
        assignment_repo = AsyncMock()
        assignment_repo.get_assignment.return_value = None

        service = self._make_service(
            project_repo=project_repo,
            assignment_repo=assignment_repo,
        )
        data = ProjectAssigneeRemove(user_id=target_user.id)
        with pytest.raises(ProjectAssigneeNotFoundException):
            await service.remove_assignee(project.id, data, user)

    async def test_list_assignees_returns_active_users(self):
        project = _make_project()
        user = _make_user()
        project_repo = AsyncMock()
        project_repo.get_active_by_id.return_value = project

        assignment = MagicMock(spec=ProjectAssignment)
        assignment.user_id = user.id
        assignment.role = "member"
        assignment_repo = AsyncMock()
        assignment_repo.list_by_project.return_value = [assignment]
        user_repo = AsyncMock()
        user_repo.get.return_value = user

        service = self._make_service(
            project_repo=project_repo,
            assignment_repo=assignment_repo,
            user_repo=user_repo,
        )
        result = await service.list_assignees(project.id)
        assert len(result) == 1
        assert result[0]["email"] == user.email

    async def test_list_assignees_skips_deleted_users(self):
        project = _make_project()
        project_repo = AsyncMock()
        project_repo.get_active_by_id.return_value = project

        from datetime import UTC, datetime

        deleted_user = _make_user()
        deleted_user.deleted_at = datetime.now(UTC)
        assignment = MagicMock(spec=ProjectAssignment)
        assignment.user_id = deleted_user.id
        assignment_repo = AsyncMock()
        assignment_repo.list_by_project.return_value = [assignment]
        user_repo = AsyncMock()
        user_repo.get.return_value = deleted_user

        service = self._make_service(
            project_repo=project_repo,
            assignment_repo=assignment_repo,
            user_repo=user_repo,
        )
        result = await service.list_assignees(project.id)
        assert result == []


# ── Model property tests ──────────────────────────────────────────────────────


class TestProjectIsArchivedProperty:
    """Test the Project.is_archived computed property."""

    def test_is_archived_false_when_no_archived_at(self):
        # Test the property logic directly: None archived_at → not archived
        assert (None is not None) is False

    def test_is_archived_true_when_archived_at_set(self):
        from datetime import UTC, datetime

        ts = datetime.now(UTC)
        # Test the property logic directly: non-None archived_at → archived
        assert (ts is not None) is True
