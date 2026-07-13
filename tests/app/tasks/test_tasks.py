"""Unit tests for TaskService."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from app.common.schemas import PaginationParams
from app.projects.exceptions import ProjectNotFoundException
from app.tasks.exceptions import TaskNotFoundException
from app.tasks.models import Task
from app.tasks.schemas import TaskCreate, TaskUpdate
from app.tasks.service import TaskService
from app.users.exceptions import UserNotFoundException


def _make_user(user_id: UUID | None = None) -> MagicMock:
    user = MagicMock()
    user.id = user_id or uuid4()
    user.email = "user@example.com"
    user.full_name = "Test User"
    user.deleted_at = None
    return user


def _make_project(project_id: UUID | None = None, org_id: UUID | None = None) -> MagicMock:
    project = MagicMock()
    project.id = project_id or uuid4()
    project.organization_id = org_id or uuid4()
    project.deleted_at = None
    return project


def _make_task(
    task_id: UUID | None = None,
    project_id: UUID | None = None,
    assignee_id: UUID | None = None,
    title: str = "Test Task",
) -> MagicMock:
    task = MagicMock(spec=Task)
    task.id = task_id or uuid4()
    task.project_id = project_id or uuid4()
    task.title = title
    task.description = None
    task.status = "todo"
    task.priority = "medium"
    task.due_date = None
    task.assignee_id = assignee_id
    task.created_by = None
    task.updated_by = None
    task.deleted_at = None
    return task


@pytest.mark.anyio
class TestTaskService:
    def _make_service(
        self,
        task_repo: Any | None = None,
        project_repo: Any | None = None,
        user_repo: Any | None = None,
    ) -> TaskService:
        return TaskService(
            task_repository=task_repo or AsyncMock(),
            project_repository=project_repo or AsyncMock(),
            user_repository=user_repo or AsyncMock(),
        )

    async def test_create_task_success(self) -> None:
        project_id = uuid4()
        project = _make_project(project_id=project_id)
        user = _make_user()
        assignee = _make_user()
        created_task = _make_task(project_id=project_id, assignee_id=assignee.id)

        project_repo = AsyncMock()
        project_repo.get_active_by_id.return_value = project
        user_repo = AsyncMock()
        user_repo.get.return_value = assignee
        task_repo = AsyncMock()
        task_repo.create.return_value = created_task

        service = self._make_service(
            task_repo=task_repo, project_repo=project_repo, user_repo=user_repo
        )
        data = TaskCreate(
            title="New Task",
            status="todo",
            priority="high",
            assignee_id=assignee.id,
        )
        result = await service.create(project_id, data, user)

        assert result is created_task
        task_repo.create.assert_awaited_once()

    async def test_create_task_project_not_found_raises(self) -> None:
        project_repo = AsyncMock()
        project_repo.get_active_by_id.return_value = None

        service = self._make_service(project_repo=project_repo)
        user = _make_user()
        data = TaskCreate(title="New Task")

        with pytest.raises(ProjectNotFoundException):
            await service.create(uuid4(), data, user)

    async def test_create_task_assignee_not_found_raises(self) -> None:
        project_id = uuid4()
        project = _make_project(project_id=project_id)
        user = _make_user()
        assignee_id = uuid4()

        project_repo = AsyncMock()
        project_repo.get_active_by_id.return_value = project
        user_repo = AsyncMock()
        user_repo.get.return_value = None

        service = self._make_service(project_repo=project_repo, user_repo=user_repo)
        data = TaskCreate(title="New Task", assignee_id=assignee_id)

        with pytest.raises(UserNotFoundException):
            await service.create(project_id, data, user)

    async def test_get_task_found(self) -> None:
        task = _make_task()
        task_repo = AsyncMock()
        task_repo.get_active_by_id.return_value = task

        service = self._make_service(task_repo=task_repo)
        result = await service.get(task.id)

        assert result is task

    async def test_get_task_not_found_raises(self) -> None:
        task_repo = AsyncMock()
        task_repo.get_active_by_id.return_value = None

        service = self._make_service(task_repo=task_repo)
        with pytest.raises(TaskNotFoundException):
            await service.get(uuid4())

    async def test_update_task_success(self) -> None:
        task = _make_task()
        updated_task = _make_task(task_id=task.id)
        updated_task.title = "Updated Task"
        user = _make_user()
        assignee = _make_user()

        task_repo = AsyncMock()
        task_repo.get_active_by_id.return_value = task
        task_repo.update.return_value = updated_task
        user_repo = AsyncMock()
        user_repo.get.return_value = assignee

        service = self._make_service(task_repo=task_repo, user_repo=user_repo)
        data = TaskUpdate(title="Updated Task", status="in_progress", assignee_id=assignee.id)
        result = await service.update(task.id, data, user)

        assert result is updated_task
        task_repo.update.assert_awaited_once()

    async def test_update_task_not_found_raises(self) -> None:
        task_repo = AsyncMock()
        task_repo.get_active_by_id.return_value = None

        service = self._make_service(task_repo=task_repo)
        user = _make_user()
        data = TaskUpdate(title="Updated Task")

        with pytest.raises(TaskNotFoundException):
            await service.update(uuid4(), data, user)

    async def test_delete_task_success(self) -> None:
        task = _make_task()
        user = _make_user()
        task_repo = AsyncMock()
        task_repo.get_active_by_id.return_value = task
        task_repo.delete_soft.return_value = task

        service = self._make_service(task_repo=task_repo)
        await service.delete(task.id, user)

        task_repo.delete_soft.assert_awaited_once_with(task)

    async def test_delete_task_not_found_raises(self) -> None:
        task_repo = AsyncMock()
        task_repo.get_active_by_id.return_value = None

        service = self._make_service(task_repo=task_repo)
        user = _make_user()

        with pytest.raises(TaskNotFoundException):
            await service.delete(uuid4(), user)

    async def test_list_tasks_success(self) -> None:
        project_id = uuid4()
        project = _make_project(project_id=project_id)
        task = _make_task(project_id=project_id)
        task_repo = AsyncMock()
        task_repo.list_by_project.return_value = ([task], MagicMock())
        project_repo = AsyncMock()
        project_repo.get_active_by_id.return_value = project

        service = self._make_service(task_repo=task_repo, project_repo=project_repo)
        pagination = PaginationParams(page=1, page_size=10)
        items, meta = await service.list_tasks(project_id, pagination)

        assert items == [task]
        task_repo.list_by_project.assert_awaited_once()

    async def test_list_tasks_project_not_found_raises(self) -> None:
        project_repo = AsyncMock()
        project_repo.get_active_by_id.return_value = None

        service = self._make_service(project_repo=project_repo)
        pagination = PaginationParams(page=1, page_size=10)

        with pytest.raises(ProjectNotFoundException):
            await service.list_tasks(uuid4(), pagination)
