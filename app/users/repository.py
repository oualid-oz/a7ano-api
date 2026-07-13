from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.repository import BaseRepository
from app.users.models import User


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, User)

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(
            User.email == email,
            User.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_by_email(self, email: str) -> User | None:
        user = await self.get_by_email(email)
        if user is None or not user.is_active:
            return None
        return user

    async def list_active(self, search: str | None = None) -> list[User]:
        stmt = select(User).where(
            User.deleted_at.is_(None),
            User.is_active.is_(True),
        )
        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(
                or_(
                    User.email.ilike(pattern),
                    User.full_name.ilike(pattern),
                )
            )
        stmt = stmt.order_by(User.full_name, User.email)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
