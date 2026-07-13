from uuid import UUID

from app.common.schemas import PaginationMeta, PaginationParams
from app.core.logging import get_logger
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

logger = get_logger(__name__)


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
        logger.info(
            "Creating team",
            extra={
                "org_id": str(organization_id),
                "team_name": data.name,
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
                "Create team failed: organization not found", extra={"org_id": str(organization_id)}
            )
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
        logger.info(
            "Team created, calling _assign_creator_role",
            extra={"team_id": str(team.id), "creator_id": str(current_user.id)},
        )
        await self._assign_creator_role(team, current_user)
        logger.info("Team created", extra={"team_id": str(team.id), "team_name": team.name})
        return team

    async def get(self, team_id: UUID) -> Team:
        logger.info("Fetching team", extra={"team_id": str(team_id)})
        team = await self._team_repository.get_active_by_id(team_id)
        if team is None:
            logger.warning("Team not found", extra={"team_id": str(team_id)})
            raise TeamNotFoundException()
        logger.info("Team fetched", extra={"team_id": str(team.id), "team_name": team.name})
        return team

    async def update(self, team_id: UUID, data: TeamUpdate, current_user: User) -> Team:
        logger.info(
            "Updating team", extra={"team_id": str(team_id), "user_id": str(current_user.id)}
        )
        team = await self.get(team_id)
        update_data = data.model_dump(exclude_unset=True)
        update_data["updated_by"] = current_user.id
        logger.info(
            "Updating team fields",
            extra={"team_id": str(team_id), "fields": list(update_data.keys())},
        )
        updated = await self._team_repository.update(team, update_data)
        logger.info("Team updated", extra={"team_id": str(updated.id)})
        return updated

    async def delete(self, team_id: UUID, current_user: User) -> Team:
        logger.info(
            "Deleting team", extra={"team_id": str(team_id), "user_id": str(current_user.id)}
        )
        team = await self.get(team_id)
        team.updated_by = current_user.id
        deleted = await self._team_repository.delete_soft(team)
        logger.info("Team deleted", extra={"team_id": str(team_id)})
        return deleted

    async def list_teams(
        self, organization_id: UUID, pagination: PaginationParams
    ) -> tuple[list[Team], PaginationMeta]:
        logger.info(
            "Listing teams", extra={"org_id": str(organization_id), "page": pagination.page}
        )
        teams, meta = await self._team_repository.list_by_organization(organization_id, pagination)
        logger.info(
            "Teams list response", extra={"org_id": str(organization_id), "total": meta.total}
        )
        return teams, meta

    async def add_member(
        self,
        team_id: UUID,
        data: TeamMemberAdd,
        current_user: User,
    ) -> UserRole:
        logger.info(
            "Adding team member", extra={"team_id": str(team_id), "user_id": str(data.user_id)}
        )
        team = await self.get(team_id)
        logger.info("Calling RoleRepository.get_or_404", extra={"role_id": str(data.role_id)})
        role = await self._role_repository.get_or_404(data.role_id)
        logger.info(
            "Checking existing membership",
            extra={"team_id": str(team_id), "user_id": str(data.user_id), "role_id": str(role.id)},
        )
        existing = await self._user_role_repository.get_assignment(
            data.user_id, role.id, team.organization_id, team_id
        )
        if existing is not None:
            logger.warning(
                "Add member failed: already a member",
                extra={"team_id": str(team_id), "user_id": str(data.user_id)},
            )
            from app.core.exceptions import DuplicateValueException

            raise DuplicateValueException("User is already a member of this team.")
        membership = UserRole(
            user_id=data.user_id,
            role_id=role.id,
            organization_id=team.organization_id,
            team_id=team_id,
        )
        result = await self._user_role_repository.create(membership)
        logger.info(
            "Team member added",
            extra={"team_id": str(team_id), "user_id": str(data.user_id), "role": role.name},
        )
        return result

    async def remove_member(
        self, team_id: UUID, data: TeamMemberRemove, current_user: User
    ) -> None:
        logger.info(
            "Removing team member", extra={"team_id": str(team_id), "user_id": str(data.user_id)}
        )
        team = await self.get(team_id)
        logger.info(
            "Checking assignment before removal",
            extra={"team_id": str(team_id), "user_id": str(data.user_id)},
        )
        assignment = await self._user_role_repository.get_assignment(
            data.user_id, data.role_id, team.organization_id, team_id
        )
        if assignment is None:
            logger.warning(
                "Remove member failed: assignment not found",
                extra={"team_id": str(team_id), "user_id": str(data.user_id)},
            )
            raise TeamMemberNotFoundException()
        await self._user_role_repository.delete_soft(assignment)
        logger.info(
            "Team member removed", extra={"team_id": str(team_id), "user_id": str(data.user_id)}
        )

    async def list_members(self, team_id: UUID) -> list[TeamMemberResponse]:
        logger.info("Listing team members", extra={"team_id": str(team_id)})
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
        logger.info("Team members listed", extra={"team_id": str(team_id), "count": len(members)})
        return members

    async def _assign_creator_role(self, team: Team, creator: User) -> None:
        logger.info(
            "Resolving creator role (team_admin or organization_admin)",
            extra={"team_id": str(team.id), "creator_id": str(creator.id)},
        )
        role = await self._role_repository.get_by_name("team_admin")
        if role is None:
            role = await self._role_repository.get_by_name("organization_admin")
        if role is None:
            logger.warning(
                "Creator role not found, skipping auto-assignment", extra={"team_id": str(team.id)}
            )
            return
        membership = UserRole(
            user_id=creator.id,
            role_id=role.id,
            organization_id=team.organization_id,
            team_id=team.id,
        )
        await self._user_role_repository.create(membership)
        logger.info(
            "Creator role assigned",
            extra={"team_id": str(team.id), "role": role.name, "creator_id": str(creator.id)},
        )
