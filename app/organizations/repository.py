from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.repository import BaseRepository
from app.organizations.models import Organization, OrganizationInvitation


class OrganizationRepository(BaseRepository[Organization]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Organization)

    async def get_by_slug(self, slug: str) -> Organization | None:
        stmt = select(Organization).where(
            Organization.slug == slug,
            Organization.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_by_id(self, org_id: UUID) -> Organization | None:
        stmt = select(Organization).where(
            Organization.id == org_id,
            Organization.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()


class InvitationRepository(BaseRepository[OrganizationInvitation]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, OrganizationInvitation)

    async def get_by_token(self, token: str) -> OrganizationInvitation | None:
        stmt = (
            select(OrganizationInvitation)
            .where(
                OrganizationInvitation.token == token,
                OrganizationInvitation.deleted_at.is_(None),
            )
            .options(
                selectinload(OrganizationInvitation.organization),
                selectinload(OrganizationInvitation.role),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_organization(self, organization_id: UUID) -> list[OrganizationInvitation]:
        stmt = (
            select(OrganizationInvitation)
            .where(
                OrganizationInvitation.organization_id == organization_id,
                OrganizationInvitation.deleted_at.is_(None),
            )
            .order_by(OrganizationInvitation.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
