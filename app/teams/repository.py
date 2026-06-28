from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.repository import BaseRepository
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

    async def list_by_organization(self, organization_id: UUID) -> list[Team]:
        stmt = select(Team).where(
            Team.organization_id == organization_id,
            Team.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
