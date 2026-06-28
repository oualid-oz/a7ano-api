from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.repository import BaseRepository
from app.permissions.models import Permission, Role, UserRole


class PermissionRepository(BaseRepository[Permission]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Permission)

    async def get_by_name(self, name: str) -> Permission | None:
        stmt = select(Permission).where(
            Permission.name == name,
            Permission.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_names(self, names: list[str]) -> list[Permission]:
        if not names:
            return []
        stmt = select(Permission).where(
            Permission.name.in_(names),
            Permission.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_resource(self, resource: str) -> list[Permission]:
        stmt = select(Permission).where(
            Permission.resource == resource,
            Permission.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())


class RoleRepository(BaseRepository[Role]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Role)

    async def get_by_name(self, name: str) -> Role | None:
        stmt = (
            select(Role)
            .where(Role.name == name, Role.deleted_at.is_(None))
            .options(selectinload(Role.permissions))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_permissions(self, role_id: UUID) -> Role | None:
        stmt = (
            select(Role)
            .where(Role.id == role_id, Role.deleted_at.is_(None))
            .options(selectinload(Role.permissions))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()


class UserRoleRepository(BaseRepository[UserRole]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, UserRole)

    async def get_assignment(
        self,
        user_id: UUID,
        role_id: UUID,
        organization_id: UUID | None,
        team_id: UUID | None,
    ) -> UserRole | None:
        stmt = select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.role_id == role_id,
            UserRole.organization_id == organization_id,
            UserRole.team_id == team_id,
            UserRole.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: UUID) -> list[UserRole]:
        stmt = (
            select(UserRole)
            .where(UserRole.user_id == user_id, UserRole.deleted_at.is_(None))
            .options(selectinload(UserRole.role).selectinload(Role.permissions))
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_user_and_scope(
        self,
        user_id: UUID,
        organization_id: UUID | None = None,
        team_id: UUID | None = None,
    ) -> list[UserRole]:
        stmt = select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.deleted_at.is_(None),
        )
        if organization_id is not None:
            stmt = stmt.where(
                (UserRole.organization_id == organization_id) | (UserRole.organization_id.is_(None))
            )
        if team_id is not None:
            stmt = stmt.where((UserRole.team_id == team_id) | (UserRole.team_id.is_(None)))
        stmt = stmt.options(selectinload(UserRole.role).selectinload(Role.permissions))
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_organization(self, organization_id: UUID) -> list[UserRole]:
        stmt = (
            select(UserRole)
            .where(
                UserRole.organization_id == organization_id,
                UserRole.deleted_at.is_(None),
            )
            .options(selectinload(UserRole.role))
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_team(self, team_id: UUID) -> list[UserRole]:
        stmt = (
            select(UserRole)
            .where(
                UserRole.team_id == team_id,
                UserRole.deleted_at.is_(None),
            )
            .options(selectinload(UserRole.role))
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
