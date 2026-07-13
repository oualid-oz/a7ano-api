from uuid import UUID

from app.common.schemas import PaginationMeta, PaginationParams
from app.core.logging import get_logger
from app.projects.repository import ProjectRepository
from app.tasks.exceptions import TaskNotFoundException
from app.tasks.models import Task
from app.tasks.repository import TaskRepository
from app.tasks.schemas import TaskCreate, TaskUpdate
from app.users.models import User
from app.users.repository import UserRepository

logger = get_logger(__name__)


class TaskService:
    def __init__(
        self,
        task_repository: TaskRepository,
        project_repository: ProjectRepository,
        user_repository: UserRepository,
    ) -> None:
        self._task_repository = task_repository
        self._project_repository = project_repository
        self._user_repository = user_repository

    async def create(self, project_id: UUID, data: TaskCreate, current_user: User) -> Task:
        logger.info(
            "Creating task",
            extra={
                "project_id": str(project_id),
                "title": data.title,
                "user_id": str(current_user.id),
            },
        )
        logger.info(
            "Calling ProjectRepository.get_active_by_id", extra={"project_id": str(project_id)}
        )
        project = await self._project_repository.get_active_by_id(project_id)
        if project is None:
            logger.warning(
                "Create task failed: project not found", extra={"project_id": str(project_id)}
            )
            from app.projects.exceptions import ProjectNotFoundException

            raise ProjectNotFoundException()

        if data.assignee_id is not None:
            logger.info(
                "Calling UserRepository.get for assignee",
                extra={"assignee_id": str(data.assignee_id)},
            )
            assignee = await self._user_repository.get(data.assignee_id)
            if assignee is None or assignee.deleted_at is not None:
                logger.warning(
                    "Create task failed: assignee not found",
                    extra={"assignee_id": str(data.assignee_id)},
                )
                from app.users.exceptions import UserNotFoundException

                raise UserNotFoundException()

        task = Task(
            project_id=project_id,
            title=data.title,
            description=data.description,
            status=data.status,
            priority=data.priority,
            due_date=data.due_date,
            assignee_id=data.assignee_id,
            created_by=current_user.id,
            updated_by=current_user.id,
        )
        task = await self._task_repository.create(task)
        logger.info(
            "Task created",
            extra={
                "task_id": str(task.id),
                "title": task.title,
                "project_id": str(task.project_id),
            },
        )
        return task

    async def get(self, task_id: UUID) -> Task:
        logger.info("Fetching task", extra={"task_id": str(task_id)})
        task = await self._task_repository.get_active_by_id(task_id)
        if task is None:
            logger.warning("Task not found", extra={"task_id": str(task_id)})
            raise TaskNotFoundException()
        logger.info("Task fetched", extra={"task_id": str(task.id), "title": task.title})
        return task

    async def update(self, task_id: UUID, data: TaskUpdate, current_user: User) -> Task:
        logger.info(
            "Updating task", extra={"task_id": str(task_id), "user_id": str(current_user.id)}
        )
        task = await self.get(task_id)
        update_data = data.model_dump(exclude_unset=True)

        if "assignee_id" in update_data and update_data["assignee_id"] is not None:
            logger.info(
                "Calling UserRepository.get for new assignee",
                extra={"assignee_id": str(update_data["assignee_id"])},
            )
            assignee = await self._user_repository.get(update_data["assignee_id"])
            if assignee is None or assignee.deleted_at is not None:
                logger.warning(
                    "Update task failed: new assignee not found",
                    extra={"assignee_id": str(update_data["assignee_id"])},
                )
                from app.users.exceptions import UserNotFoundException

                raise UserNotFoundException()

        update_data["updated_by"] = current_user.id
        logger.info(
            "Updating task fields",
            extra={"task_id": str(task_id), "fields": list(update_data.keys())},
        )
        updated = await self._task_repository.update(task, update_data)
        logger.info("Task updated", extra={"task_id": str(updated.id)})
        return updated

    async def delete(self, task_id: UUID, current_user: User) -> Task:
        logger.info(
            "Deleting task", extra={"task_id": str(task_id), "user_id": str(current_user.id)}
        )
        task = await self.get(task_id)
        task.updated_by = current_user.id
        deleted = await self._task_repository.delete_soft(task)
        logger.info("Task deleted", extra={"task_id": str(task_id)})
        return deleted

    async def list_tasks(
        self,
        project_id: UUID,
        pagination: PaginationParams,
        status: str | None = None,
        priority: str | None = None,
        assignee_id: UUID | None = None,
    ) -> tuple[list[Task], PaginationMeta]:
        logger.info(
            "Listing tasks",
            extra={
                "project_id": str(project_id),
                "status": status,
                "priority": priority,
                "page": pagination.page,
            },
        )
        project = await self._project_repository.get_active_by_id(project_id)
        if project is None:
            logger.warning(
                "List tasks failed: project not found", extra={"project_id": str(project_id)}
            )
            from app.projects.exceptions import ProjectNotFoundException

            raise ProjectNotFoundException()

        tasks, meta = await self._task_repository.list_by_project(
            project_id=project_id,
            pagination=pagination,
            status=status,
            priority=priority,
            assignee_id=assignee_id,
        )
        logger.info(
            "Tasks list response", extra={"project_id": str(project_id), "total": meta.total}
        )
        return tasks, meta
