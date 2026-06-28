from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.repository import BaseRepository
from app.common.schemas import PaginationMeta, PaginationParams
from app.memos.models import Memo, MemoFolder, MemoTag, MemoVersion


class MemoFolderRepository(BaseRepository[MemoFolder]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, MemoFolder)

    async def get_by_name_and_owner(self, name: str, owner_id: UUID) -> MemoFolder | None:
        stmt = select(MemoFolder).where(
            MemoFolder.name == name,
            MemoFolder.owner_id == owner_id,
            MemoFolder.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_organization_and_owner(
        self, organization_id: UUID, owner_id: UUID
    ) -> list[MemoFolder]:
        stmt = (
            select(MemoFolder)
            .where(
                MemoFolder.organization_id == organization_id,
                MemoFolder.owner_id == owner_id,
                MemoFolder.deleted_at.is_(None),
            )
            .order_by(MemoFolder.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())


class MemoTagRepository(BaseRepository[MemoTag]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, MemoTag)

    async def get_by_name_and_org(self, name: str, organization_id: UUID) -> MemoTag | None:
        stmt = select(MemoTag).where(
            MemoTag.name == name,
            MemoTag.organization_id == organization_id,
            MemoTag.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_organization(self, organization_id: UUID) -> list[MemoTag]:
        stmt = select(MemoTag).where(
            MemoTag.organization_id == organization_id,
            MemoTag.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_many_by_ids(self, ids: list[UUID]) -> list[MemoTag]:
        if not ids:
            return []
        stmt = select(MemoTag).where(
            MemoTag.id.in_(ids),
            MemoTag.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())


class MemoRepository(BaseRepository[Memo]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Memo)

    async def get_active_by_id(self, memo_id: UUID) -> Memo | None:
        stmt = (
            select(Memo)
            .where(Memo.id == memo_id, Memo.deleted_at.is_(None))
            .options(
                selectinload(Memo.tags),
                selectinload(Memo.versions),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_organization(
        self,
        organization_id: UUID,
        pagination: PaginationParams,
        owner_id: UUID | None = None,
        folder_id: UUID | None = None,
        is_pinned: bool | None = None,
        is_favorite: bool | None = None,
        search: str | None = None,
    ) -> tuple[list[Memo], PaginationMeta]:
        stmt = select(Memo).where(
            Memo.organization_id == organization_id,
            Memo.deleted_at.is_(None),
        )

        if owner_id is not None:
            stmt = stmt.where(Memo.owner_id == owner_id)
        if folder_id is not None:
            stmt = stmt.where(Memo.folder_id == folder_id)
        if is_pinned is not None:
            stmt = stmt.where(Memo.is_pinned == is_pinned)
        if is_favorite is not None:
            stmt = stmt.where(Memo.is_favorite == is_favorite)
        if search:
            stmt = stmt.where(Memo.title.ilike(f"%{search}%"))

        stmt = stmt.options(
            selectinload(Memo.tags),
            selectinload(Memo.versions),
        )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar_one()

        sort_attr = pagination.sort or "created_at"
        if not hasattr(Memo, sort_attr):
            sort_attr = "created_at"
        sort_column = getattr(Memo, sort_attr)
        stmt = stmt.order_by(desc(sort_column))

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


class MemoVersionRepository(BaseRepository[MemoVersion]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, MemoVersion)

    async def list_by_memo(self, memo_id: UUID) -> list[MemoVersion]:
        stmt = (
            select(MemoVersion)
            .where(
                MemoVersion.memo_id == memo_id,
                MemoVersion.deleted_at.is_(None),
            )
            .order_by(MemoVersion.version_number.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
