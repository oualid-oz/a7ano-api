from datetime import UTC, datetime
from uuid import UUID

from app.common.schemas import PaginationMeta, PaginationParams
from app.core.exceptions import DuplicateValueException
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
    ProjectUpdate,
)
from app.users.models import User
from app.users.repository import UserRepository


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

    async def delete(self, tag_id: UUID) -> None:
        tag = await self._tag_repository.get(tag_id)
        if tag is None or tag.deleted_at is not None:
            raise ProjectTagNotFoundException()
        await self._tag_repository.delete_soft(tag)


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
        organization = await self._organization_repository.get_active_by_id(organization_id)
        if organization is None:
            from app.organizations.exceptions import OrganizationNotFoundException

            raise OrganizationNotFoundException()

        tags: list[ProjectTag] = []
        if data.tag_ids:
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
        # Auto-assign creator as owner
        assignment = ProjectAssignment(
            project_id=project.id,
            user_id=current_user.id,
            role="owner",
        )
        await self._assignment_repository.create(assignment)
        return await self._project_repository.get_active_by_id(project.id) or project

    async def get(self, project_id: UUID) -> Project:
        project = await self._project_repository.get_active_by_id(project_id)
        if project is None:
            raise ProjectNotFoundException()
        return project

    async def update(
        self,
        project_id: UUID,
        data: ProjectUpdate,
        current_user: User,
    ) -> Project:
        project = await self.get(project_id)
        update_data = data.model_dump(exclude_unset=True)

        if "tag_ids" in update_data:
            tag_ids = update_data.pop("tag_ids")
            project.tags = await self._tag_repository.get_many_by_ids(tag_ids)

        update_data["updated_by"] = current_user.id
        return await self._project_repository.update(project, update_data)

    async def delete(self, project_id: UUID, current_user: User) -> Project:
        project = await self.get(project_id)
        project.updated_by = current_user.id
        return await self._project_repository.delete_soft(project)

    async def archive(self, project_id: UUID, current_user: User) -> Project:
        project = await self.get(project_id)
        if project.archived_at is not None:
            raise DuplicateValueException("Project is already archived.")
        project.archived_at = datetime.now(UTC)
        project.updated_by = current_user.id
        return await self._project_repository.update(project, {
            "archived_at": project.archived_at,
            "updated_by": current_user.id,
        })

    async def restore(self, project_id: UUID, current_user: User) -> Project:
        project = await self.get(project_id)
        if project.archived_at is None:
            raise DuplicateValueException("Project is not archived.")
        return await self._project_repository.update(project, {
            "archived_at": None,
            "updated_by": current_user.id,
        })

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
        return await self._project_repository.list_by_organization(
            organization_id=organization_id,
            pagination=pagination,
            status=status,
            priority=priority,
            team_id=team_id,
            search=search,
            include_archived=include_archived,
        )

    async def add_assignee(
        self,
        project_id: UUID,
        data: ProjectAssigneeAdd,
        current_user: User,
    ) -> ProjectAssignment:
        project = await self.get(project_id)
        user = await self._user_repository.get(data.user_id)
        if user is None or user.deleted_at is not None:
            from app.users.exceptions import UserNotFoundException

            raise UserNotFoundException()
        existing = await self._assignment_repository.get_assignment(project.id, data.user_id)
        if existing is not None:
            raise DuplicateValueException("User is already assigned to this project.")
        assignment = ProjectAssignment(
            project_id=project.id,
            user_id=data.user_id,
            role=data.role,
        )
        return await self._assignment_repository.create(assignment)

    async def remove_assignee(
        self,
        project_id: UUID,
        data: ProjectAssigneeRemove,
        current_user: User,
    ) -> None:
        project = await self.get(project_id)
        assignment = await self._assignment_repository.get_assignment(project.id, data.user_id)
        if assignment is None:
            raise ProjectAssigneeNotFoundException()
        await self._assignment_repository.delete_soft(assignment)

    async def list_assignees(self, project_id: UUID) -> list[dict]:
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
        return result
