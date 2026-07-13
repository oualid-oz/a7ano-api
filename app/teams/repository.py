from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.repository import BaseRepository
from app.common.schemas import PaginationMeta, PaginationParams
from app.teams.models import Team


class TeamRepository(BaseRepository[Team]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Team)

    async def get_active_by_id(self, team_id: UUID) -> Team | None:
        stmt = (
            select(Team)
            .where(Team.id == team_id, Team.deleted_at.is_(None))
            .options(selectinload(Team.organization))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_organization(
        self, organization_id: UUID, pagination: PaginationParams
    ) -> tuple[list[Team], PaginationMeta]:
        return await self.list(
            pagination=pagination,
            filters={"organization_id": organization_id},
            sort_field="created_at",
            sort_desc=True,
        )
