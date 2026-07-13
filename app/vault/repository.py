from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.repository import BaseRepository
from app.common.schemas import PaginationMeta, PaginationParams
from app.vault.models import (
    VaultAccessLog,
    VaultCategory,
    VaultEntry,
    VaultShare,
    VaultTag,
)


class VaultCategoryRepository(BaseRepository[VaultCategory]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, VaultCategory)

    async def list_by_organization(self, org_id: UUID) -> list[VaultCategory]:
        stmt = select(VaultCategory).where(
            VaultCategory.organization_id == org_id,
            VaultCategory.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())


class VaultTagRepository(BaseRepository[VaultTag]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, VaultTag)

    async def list_by_organization(self, org_id: UUID) -> list[VaultTag]:
        stmt = select(VaultTag).where(
            VaultTag.organization_id == org_id,
            VaultTag.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_many_by_ids(self, ids: list[UUID]) -> list[VaultTag]:
        if not ids:
            return []
        stmt = select(VaultTag).where(
            VaultTag.id.in_(ids),
            VaultTag.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_name_and_org(self, name: str, org_id: UUID) -> VaultTag | None:
        stmt = select(VaultTag).where(
            VaultTag.name == name,
            VaultTag.organization_id == org_id,
            VaultTag.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()


class VaultEntryRepository(BaseRepository[VaultEntry]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, VaultEntry)

    async def get_active_by_id(self, entry_id: UUID) -> VaultEntry | None:
        stmt = (
            select(VaultEntry)
            .where(VaultEntry.id == entry_id, VaultEntry.deleted_at.is_(None))
            .options(selectinload(VaultEntry.tags), selectinload(VaultEntry.category))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_owner(
        self,
        owner_id: UUID,
        pagination: PaginationParams,
        organization_id: UUID | None = None,
        entry_type: str | None = None,
        category_id: UUID | None = None,
        search: str | None = None,
    ) -> tuple[list[VaultEntry], PaginationMeta]:
        stmt = (
            select(VaultEntry)
            .where(
                VaultEntry.owner_id == owner_id,
                VaultEntry.deleted_at.is_(None),
            )
            .options(selectinload(VaultEntry.tags), selectinload(VaultEntry.category))
        )
        if organization_id is not None:
            stmt = stmt.where(VaultEntry.organization_id == organization_id)
        if entry_type is not None:
            stmt = stmt.where(VaultEntry.entry_type == entry_type)
        if category_id is not None:
            stmt = stmt.where(VaultEntry.category_id == category_id)
        if search is not None:
            stmt = stmt.where(VaultEntry.title.ilike(f"%{search}%"))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = stmt.order_by(desc(VaultEntry.created_at))
        offset = (pagination.page - 1) * pagination.page_size
        stmt = stmt.offset(offset).limit(pagination.page_size)
        result = await self._session.execute(stmt)
        items = list(result.scalars().all())

        pages = (total + pagination.page_size - 1) // pagination.page_size
        meta = PaginationMeta(
            page=pagination.page,
            page_size=pagination.page_size,
            total=total,
            pages=pages or 1,
        )
        return items, meta

    async def list_for_user(
        self,
        user_id: UUID,
        pagination: PaginationParams,
        organization_id: UUID | None = None,
        entry_type: str | None = None,
        category_id: UUID | None = None,
        search: str | None = None,
    ) -> tuple[list[VaultEntry], PaginationMeta]:
        owned_ids = select(VaultEntry.id).where(
            VaultEntry.owner_id == user_id,
            VaultEntry.deleted_at.is_(None),
        )
        shared_ids = (
            select(VaultEntry.id)
            .join(VaultShare, VaultShare.entry_id == VaultEntry.id)
            .where(
                VaultEntry.deleted_at.is_(None),
                VaultShare.deleted_at.is_(None),
                VaultShare.shared_with_user_id == user_id,
            )
        )
        visible_ids = owned_ids.union(shared_ids)

        stmt = (
            select(VaultEntry)
            .where(
                VaultEntry.id.in_(visible_ids),
                VaultEntry.deleted_at.is_(None),
            )
            .options(selectinload(VaultEntry.tags), selectinload(VaultEntry.category))
        )
        if organization_id is not None:
            stmt = stmt.where(VaultEntry.organization_id == organization_id)
        if entry_type is not None:
            stmt = stmt.where(VaultEntry.entry_type == entry_type)
        if category_id is not None:
            stmt = stmt.where(VaultEntry.category_id == category_id)
        if search is not None:
            stmt = stmt.where(VaultEntry.title.ilike(f"%{search}%"))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = stmt.order_by(desc(VaultEntry.created_at))
        offset = (pagination.page - 1) * pagination.page_size
        stmt = stmt.offset(offset).limit(pagination.page_size)
        result = await self._session.execute(stmt)
        items = list(result.scalars().all())

        pages = (total + pagination.page_size - 1) // pagination.page_size
        meta = PaginationMeta(
            page=pagination.page,
            page_size=pagination.page_size,
            total=total,
            pages=pages or 1,
        )
        return items, meta

    async def list_shared_with_user(
        self,
        user_id: UUID,
        pagination: PaginationParams,
        organization_id: UUID | None = None,
        entry_type: str | None = None,
        category_id: UUID | None = None,
        search: str | None = None,
    ) -> tuple[list[VaultEntry], PaginationMeta]:
        stmt = (
            select(VaultEntry)
            .join(VaultShare, VaultShare.entry_id == VaultEntry.id)
            .where(
                VaultEntry.deleted_at.is_(None),
                VaultShare.deleted_at.is_(None),
                VaultShare.shared_with_user_id == user_id,
            )
            .options(selectinload(VaultEntry.tags), selectinload(VaultEntry.category))
        )
        if organization_id is not None:
            stmt = stmt.where(VaultEntry.organization_id == organization_id)
        if entry_type is not None:
            stmt = stmt.where(VaultEntry.entry_type == entry_type)
        if category_id is not None:
            stmt = stmt.where(VaultEntry.category_id == category_id)
        if search is not None:
            stmt = stmt.where(VaultEntry.title.ilike(f"%{search}%"))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = stmt.order_by(desc(VaultEntry.created_at))
        offset = (pagination.page - 1) * pagination.page_size
        stmt = stmt.offset(offset).limit(pagination.page_size)
        result = await self._session.execute(stmt)
        items = list(result.scalars().all())

        pages = (total + pagination.page_size - 1) // pagination.page_size
        meta = PaginationMeta(
            page=pagination.page,
            page_size=pagination.page_size,
            total=total,
            pages=pages or 1,
        )
        return items, meta


class VaultShareRepository(BaseRepository[VaultShare]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, VaultShare)

    async def list_by_entry(self, entry_id: UUID) -> list[VaultShare]:
        stmt = (
            select(VaultShare)
            .where(VaultShare.entry_id == entry_id, VaultShare.deleted_at.is_(None))
            .options(selectinload(VaultShare.shared_with_user))
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_share(self, entry_id: UUID, user_id: UUID) -> VaultShare | None:
        stmt = select(VaultShare).where(
            VaultShare.entry_id == entry_id,
            VaultShare.shared_with_user_id == user_id,
            VaultShare.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()


class VaultAccessLogRepository(BaseRepository[VaultAccessLog]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, VaultAccessLog)

    async def create_log(
        self,
        entry_id: UUID,
        user_id: UUID,
        action: str,
        ip: str | None,
        user_agent: str | None,
    ) -> VaultAccessLog:
        log = VaultAccessLog(
            entry_id=entry_id,
            user_id=user_id,
            action=action,
            ip_address=ip,
            user_agent=user_agent,
        )
        return await self.create(log)

    async def list_by_entry(self, entry_id: UUID, limit: int = 50) -> list[VaultAccessLog]:
        stmt = (
            select(VaultAccessLog)
            .where(VaultAccessLog.entry_id == entry_id)
            .options(selectinload(VaultAccessLog.user))
            .order_by(desc(VaultAccessLog.created_at))
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
