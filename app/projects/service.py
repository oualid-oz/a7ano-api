from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.common.schemas import PaginationMeta, PaginationParams
from app.core.exceptions import DuplicateValueException
from app.core.logging import get_logger
from app.organizations.repository import OrganizationRepository
from app.projects.exceptions import (
    ProjectAssigneeNotFoundException,
    ProjectNotFoundException,
    ProjectTagNotFoundException,
)
from app.projects.models import Project, ProjectAssignment, ProjectTag
from app.projects.repository import (
    ProjectAssignmentRepository,
    ProjectRepository,
    ProjectTagRepository,
)
from app.projects.schemas import (
    ProjectAssigneeAdd,
    ProjectAssigneeRemove,
    ProjectCreate,
    ProjectTagCreate,
    ProjectTagUpdate,
    ProjectUpdate,
)
from app.users.models import User
from app.users.repository import UserRepository

logger = get_logger(__name__)


class ProjectTagService:
    def __init__(
        self,
        tag_repository: ProjectTagRepository,
        organization_repository: OrganizationRepository,
    ) -> None:
        self._tag_repository = tag_repository
        self._organization_repository = organization_repository

    async def create(
        self,
        organization_id: UUID,
        data: ProjectTagCreate,
        current_user: User,
    ) -> ProjectTag:
        logger.info(
            "Creating project tag", extra={"org_id": str(organization_id), "tag_name": data.name}
        )
        organization = await self._organization_repository.get_active_by_id(organization_id)
        if organization is None:
            from app.organizations.exceptions import OrganizationNotFoundException

            raise OrganizationNotFoundException()
        existing = await self._tag_repository.get_by_name_and_org(data.name, organization_id)
        if existing is not None:
            raise DuplicateValueException(
                "A tag with this name already exists in the organization."
            )
        tag = ProjectTag(
            organization_id=organization_id,
            name=data.name,
            color=data.color,
        )
        return await self._tag_repository.create(tag)

    async def list_tags(self, organization_id: UUID) -> list[ProjectTag]:
        return await self._tag_repository.list_by_organization(organization_id)

    async def update(self, tag_id: UUID, data: ProjectTagUpdate, current_user: User) -> ProjectTag:
        logger.info(
            "Updating project tag", extra={"tag_id": str(tag_id), "user_id": str(current_user.id)}
        )
        tag = await self._tag_repository.get(tag_id)
        if tag is None or tag.deleted_at is not None:
            logger.warning("Update tag failed: not found", extra={"tag_id": str(tag_id)})
            raise ProjectTagNotFoundException()

        update_data = data.model_dump(exclude_unset=True)
        if "name" in update_data:
            existing = await self._tag_repository.get_by_name_and_org(
                update_data["name"], tag.organization_id
            )
            if existing is not None and existing.id != tag.id:
                raise DuplicateValueException(
                    "A tag with this name already exists in the organization."
                )

        return await self._tag_repository.update(tag, update_data)

    async def delete(self, tag_id: UUID) -> None:
        logger.info("Deleting project tag", extra={"tag_id": str(tag_id)})
        tag = await self._tag_repository.get(tag_id)
        if tag is None or tag.deleted_at is not None:
            logger.warning("Delete tag failed: not found", extra={"tag_id": str(tag_id)})
            raise ProjectTagNotFoundException()
        await self._tag_repository.delete_soft(tag)
        logger.info("Project tag deleted", extra={"tag_id": str(tag_id)})


class ProjectService:
    def __init__(
        self,
        project_repository: ProjectRepository,
        tag_repository: ProjectTagRepository,
        assignment_repository: ProjectAssignmentRepository,
        organization_repository: OrganizationRepository,
        user_repository: UserRepository,
    ) -> None:
        self._project_repository = project_repository
        self._tag_repository = tag_repository
        self._assignment_repository = assignment_repository
        self._organization_repository = organization_repository
        self._user_repository = user_repository

    async def create(
        self,
        organization_id: UUID,
        data: ProjectCreate,
        current_user: User,
    ) -> Project:
        logger.info(
            "Creating project",
            extra={
                "org_id": str(organization_id),
                "title": data.title,
                "user_id": str(current_user.id),
            },
        )
        logger.info(
            "Calling OrganizationRepository.get_active_by_id",
            extra={"org_id": str(organization_id)},
        )
        organization = await self._organization_repository.get_active_by_id(organization_id)
        if organization is None:
            logger.warning(
                "Create project failed: organization not found",
                extra={"org_id": str(organization_id)},
            )
            from app.organizations.exceptions import OrganizationNotFoundException

            raise OrganizationNotFoundException()

        tags: list[ProjectTag] = []
        if data.tag_ids:
            logger.info("Resolving tag_ids", extra={"tag_ids": [str(t) for t in data.tag_ids]})
            tags = await self._tag_repository.get_many_by_ids(data.tag_ids)

        project = Project(
            organization_id=organization_id,
            team_id=data.team_id,
            owner_id=current_user.id,
            title=data.title,
            description=data.description,
            status=data.status,
            priority=data.priority,
            due_date=data.due_date,
            created_by=current_user.id,
            updated_by=current_user.id,
            tags=tags,
        )
        project = await self._project_repository.create(project)
        logger.info(
            "Project row created, auto-assigning creator as owner",
            extra={"project_id": str(project.id)},
        )
        assignment = ProjectAssignment(
            project_id=project.id,
            user_id=current_user.id,
            role="owner",
        )
        await self._assignment_repository.create(assignment)
        result = await self._project_repository.get_active_by_id(project.id) or project
        logger.info("Project created", extra={"project_id": str(result.id), "title": result.title})
        return result

    async def get(self, project_id: UUID) -> Project:
        logger.info("Fetching project", extra={"project_id": str(project_id)})
        project = await self._project_repository.get_active_by_id(project_id)
        if project is None:
            logger.warning("Project not found", extra={"project_id": str(project_id)})
            raise ProjectNotFoundException()
        logger.info(
            "Project fetched", extra={"project_id": str(project.id), "title": project.title}
        )
        return project

    async def update(
        self,
        project_id: UUID,
        data: ProjectUpdate,
        current_user: User,
    ) -> Project:
        logger.info(
            "Updating project",
            extra={"project_id": str(project_id), "user_id": str(current_user.id)},
        )
        project = await self.get(project_id)
        update_data = data.model_dump(exclude_unset=True)

        if "tag_ids" in update_data:
            tag_ids = update_data.pop("tag_ids")
            logger.info(
                "Resolving updated tag_ids",
                extra={"project_id": str(project_id), "tag_ids": [str(t) for t in tag_ids]},
            )
            project.tags = await self._tag_repository.get_many_by_ids(tag_ids)

        update_data["updated_by"] = current_user.id
        logger.info(
            "Updating project fields",
            extra={"project_id": str(project_id), "fields": list(update_data.keys())},
        )
        updated = await self._project_repository.update(project, update_data)
        logger.info("Project updated", extra={"project_id": str(updated.id)})
        return updated

    async def delete(self, project_id: UUID, current_user: User) -> Project:
        logger.info(
            "Deleting project",
            extra={"project_id": str(project_id), "user_id": str(current_user.id)},
        )
        project = await self.get(project_id)
        project.updated_by = current_user.id
        deleted = await self._project_repository.delete_soft(project)
        logger.info("Project deleted", extra={"project_id": str(project_id)})
        return deleted

    async def archive(self, project_id: UUID, current_user: User) -> Project:
        logger.info(
            "Archiving project",
            extra={"project_id": str(project_id), "user_id": str(current_user.id)},
        )
        project = await self.get(project_id)
        if project.archived_at is not None:
            raise DuplicateValueException("Project is already archived.")
        project.archived_at = datetime.now(UTC)
        project.updated_by = current_user.id
        return await self._project_repository.update(
            project,
            {
                "archived_at": project.archived_at,
                "updated_by": current_user.id,
            },
        )

    async def restore(self, project_id: UUID, current_user: User) -> Project:
        logger.info(
            "Restoring project",
            extra={"project_id": str(project_id), "user_id": str(current_user.id)},
        )
        project = await self.get(project_id)
        if project.archived_at is None:
            raise DuplicateValueException("Project is not archived.")
        return await self._project_repository.update(
            project,
            {
                "archived_at": None,
                "updated_by": current_user.id,
            },
        )

    async def list_projects(
        self,
        organization_id: UUID,
        pagination: PaginationParams,
        status: str | None = None,
        priority: str | None = None,
        team_id: UUID | None = None,
        search: str | None = None,
        include_archived: bool = False,
    ) -> tuple[list[Project], PaginationMeta]:
        logger.info(
            "Listing projects",
            extra={
                "org_id": str(organization_id),
                "status": status,
                "priority": priority,
                "team_id": str(team_id) if team_id else None,
                "search": search,
                "page": pagination.page,
            },
        )
        projects, meta = await self._project_repository.list_by_organization(
            organization_id=organization_id,
            pagination=pagination,
            status=status,
            priority=priority,
            team_id=team_id,
            search=search,
            include_archived=include_archived,
        )
        logger.info(
            "Projects list response", extra={"org_id": str(organization_id), "total": meta.total}
        )
        return projects, meta

    async def add_assignee(
        self,
        project_id: UUID,
        data: ProjectAssigneeAdd,
        current_user: User,
    ) -> ProjectAssignment:
        logger.info(
            "Adding project assignee",
            extra={"project_id": str(project_id), "user_id": str(data.user_id), "role": data.role},
        )
        project = await self.get(project_id)
        logger.info("Calling UserRepository.get for assignee", extra={"user_id": str(data.user_id)})
        user = await self._user_repository.get(data.user_id)
        if user is None or user.deleted_at is not None:
            logger.warning(
                "Add assignee failed: user not found", extra={"user_id": str(data.user_id)}
            )
            from app.users.exceptions import UserNotFoundException

            raise UserNotFoundException()
        existing = await self._assignment_repository.get_assignment(project.id, data.user_id)
        if existing is not None:
            logger.warning(
                "Add assignee failed: already assigned",
                extra={"project_id": str(project_id), "user_id": str(data.user_id)},
            )
            raise DuplicateValueException("User is already assigned to this project.")
        assignment = ProjectAssignment(
            project_id=project.id,
            user_id=data.user_id,
            role=data.role,
        )
        result = await self._assignment_repository.create(assignment)
        logger.info(
            "Project assignee added",
            extra={"project_id": str(project_id), "user_id": str(data.user_id)},
        )
        return result

    async def remove_assignee(
        self,
        project_id: UUID,
        data: ProjectAssigneeRemove,
        current_user: User,
    ) -> None:
        logger.info(
            "Removing project assignee",
            extra={"project_id": str(project_id), "user_id": str(data.user_id)},
        )
        project = await self.get(project_id)
        assignment = await self._assignment_repository.get_assignment(project.id, data.user_id)
        if assignment is None:
            logger.warning(
                "Remove assignee failed: not found",
                extra={"project_id": str(project_id), "user_id": str(data.user_id)},
            )
            raise ProjectAssigneeNotFoundException()
        await self._assignment_repository.delete_soft(assignment)
        logger.info(
            "Project assignee removed",
            extra={"project_id": str(project_id), "user_id": str(data.user_id)},
        )

    async def list_assignees(self, project_id: UUID) -> list[dict[str, Any]]:
        logger.info("Listing project assignees", extra={"project_id": str(project_id)})
        project = await self.get(project_id)
        assignments = await self._assignment_repository.list_by_project(project.id)
        result = []
        for assignment in assignments:
            user = await self._user_repository.get(assignment.user_id)
            if user is None or user.deleted_at is not None:
                continue
            result.append(
                {
                    "user_id": user.id,
                    "full_name": user.full_name,
                    "email": user.email,
                    "role": assignment.role,
                }
            )
        logger.info(
            "Project assignees listed", extra={"project_id": str(project_id), "count": len(result)}
        )
        return result
