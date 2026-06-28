from uuid import UUID

from app.common.schemas import PaginationMeta, PaginationParams
from app.organizations.repository import OrganizationRepository
from app.permissions.models import UserRole
from app.permissions.repository import RoleRepository, UserRoleRepository
from app.teams.exceptions import TeamMemberNotFoundException, TeamNotFoundException
from app.teams.models import Team
from app.teams.repository import TeamRepository
from app.teams.schemas import (
    TeamCreate,
    TeamMemberAdd,
    TeamMemberRemove,
    TeamMemberResponse,
    TeamUpdate,
)
from app.users.models import User
from app.users.repository import UserRepository


class TeamService:
    def __init__(
        self,
        team_repository: TeamRepository,
        organization_repository: OrganizationRepository,
        role_repository: RoleRepository,
        user_role_repository: UserRoleRepository,
        user_repository: UserRepository,
    ) -> None:
        self._team_repository = team_repository
        self._organization_repository = organization_repository
        self._role_repository = role_repository
        self._user_role_repository = user_role_repository
        self._user_repository = user_repository

    async def create(
        self,
        organization_id: UUID,
        data: TeamCreate,
        current_user: User,
    ) -> Team:
        organization = await self._organization_repository.get_active_by_id(organization_id)
        if organization is None:
            from app.organizations.exceptions import OrganizationNotFoundException

            raise OrganizationNotFoundException()

        team = Team(
            organization_id=organization_id,
            name=data.name,
            description=data.description,
            created_by=current_user.id,
            updated_by=current_user.id,
        )
        team = await self._team_repository.create(team)
        await self._assign_creator_role(team, current_user)
        return team

    async def get(self, team_id: UUID) -> Team:
        team = await self._team_repository.get_active_by_id(team_id)
        if team is None:
            raise TeamNotFoundException()
        return team

    async def update(self, team_id: UUID, data: TeamUpdate, current_user: User) -> Team:
        team = await self.get(team_id)
        update_data = data.model_dump(exclude_unset=True)
        update_data["updated_by"] = current_user.id
        return await self._team_repository.update(team, update_data)

    async def delete(self, team_id: UUID, current_user: User) -> Team:
        team = await self.get(team_id)
        team.updated_by = current_user.id
        return await self._team_repository.delete_soft(team)

    async def list_teams(
        self, organization_id: UUID, pagination: PaginationParams
    ) -> tuple[list[Team], PaginationMeta]:
        return await self._team_repository.list(pagination)

    async def add_member(
        self,
        team_id: UUID,
        data: TeamMemberAdd,
        current_user: User,
    ) -> UserRole:
        team = await self.get(team_id)
        role = await self._role_repository.get_or_404(data.role_id)
        existing = await self._user_role_repository.get_assignment(
            data.user_id, role.id, team.organization_id, team_id
        )
        if existing is not None:
            from app.core.exceptions import DuplicateValueException

            raise DuplicateValueException("User is already a member of this team.")
        membership = UserRole(
            user_id=data.user_id,
            role_id=role.id,
            organization_id=team.organization_id,
            team_id=team_id,
        )
        return await self._user_role_repository.create(membership)

    async def remove_member(
        self, team_id: UUID, data: TeamMemberRemove, current_user: User
    ) -> None:
        team = await self.get(team_id)
        assignment = await self._user_role_repository.get_assignment(
            data.user_id, data.role_id, team.organization_id, team_id
        )
        if assignment is None:
            raise TeamMemberNotFoundException()
        await self._user_role_repository.delete_soft(assignment)

    async def list_members(self, team_id: UUID) -> list[TeamMemberResponse]:
        await self.get(team_id)
        assignments = await self._user_role_repository.list_by_team(team_id)
        members: list[TeamMemberResponse] = []
        for assignment in assignments:
            user = await self._user_repository.get(assignment.user_id)
            if user is None or user.deleted_at is not None:
                continue
            members.append(
                TeamMemberResponse(
                    user_id=user.id,
                    full_name=user.full_name,
                    email=user.email,
                    role_id=assignment.role_id,
                    role_name=assignment.role.name,
                )
            )
        return members

    async def _assign_creator_role(self, team: Team, creator: User) -> None:
        role = await self._role_repository.get_by_name("team_admin")
        if role is None:
            role = await self._role_repository.get_by_name("organization_admin")
        if role is None:
            return
        membership = UserRole(
            user_id=creator.id,
            role_id=role.id,
            organization_id=team.organization_id,
            team_id=team.id,
        )
        await self._user_role_repository.create(membership)
