from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import RefreshSession
from app.common.repository import BaseRepository


class RefreshSessionRepository(BaseRepository[RefreshSession]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, RefreshSession)

    async def get_by_token_hash(self, token_hash: str) -> RefreshSession | None:
        stmt = select(RefreshSession).where(
            RefreshSession.token_hash == token_hash,
            RefreshSession.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke(self, session: RefreshSession) -> RefreshSession:
        session.revoke()
        await self._session.flush()
        await self._session.refresh(session)
        return session

    async def revoke_all_for_user(self, user_id: UUID) -> None:
        stmt = (
            update(RefreshSession)
            .where(
                RefreshSession.user_id == user_id,
                RefreshSession.revoked_at.is_(None),
                RefreshSession.deleted_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def list_by_user(self, user_id: UUID) -> list[RefreshSession]:
        stmt = (
            select(RefreshSession)
            .where(
                RefreshSession.user_id == user_id,
                RefreshSession.deleted_at.is_(None),
            )
            .order_by(RefreshSession.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
