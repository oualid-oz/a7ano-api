from uuid import UUID

from app.common.schemas import PaginationMeta, PaginationParams
from app.core.exceptions import DuplicateValueException
from app.memos.exceptions import (
    MemoFolderNotFoundException,
    MemoNotFoundException,
    MemoTagNotFoundException,
)
from app.memos.models import Memo, MemoFolder, MemoTag, MemoVersion
from app.memos.repository import (
    MemoFolderRepository,
    MemoRepository,
    MemoTagRepository,
    MemoVersionRepository,
)
from app.memos.schemas import MemoCreate, MemoFolderCreate, MemoTagCreate, MemoUpdate
from app.organizations.repository import OrganizationRepository
from app.users.models import User


class MemoFolderService:
    def __init__(
        self,
        folder_repository: MemoFolderRepository,
        organization_repository: OrganizationRepository,
    ) -> None:
        self._folder_repository = folder_repository
        self._organization_repository = organization_repository

    async def create(
        self,
        organization_id: UUID,
        data: MemoFolderCreate,
        current_user: User,
    ) -> MemoFolder:
        organization = await self._organization_repository.get_active_by_id(organization_id)
        if organization is None:
            from app.organizations.exceptions import OrganizationNotFoundException

            raise OrganizationNotFoundException()

        folder = MemoFolder(
            organization_id=organization_id,
            owner_id=current_user.id,
            name=data.name,
            parent_id=data.parent_id,
        )
        return await self._folder_repository.create(folder)

    async def list_folders(
        self, organization_id: UUID, owner_id: UUID
    ) -> list[MemoFolder]:
        return await self._folder_repository.list_by_organization_and_owner(
            organization_id, owner_id
        )

    async def delete(self, folder_id: UUID, current_user: User) -> None:
        folder = await self._folder_repository.get(folder_id)
        if folder is None or folder.deleted_at is not None:
            raise MemoFolderNotFoundException()
        await self._folder_repository.delete_soft(folder)


class MemoTagService:
    def __init__(
        self,
        tag_repository: MemoTagRepository,
        organization_repository: OrganizationRepository,
    ) -> None:
        self._tag_repository = tag_repository
        self._organization_repository = organization_repository

    async def create(
        self,
        organization_id: UUID,
        data: MemoTagCreate,
        current_user: User,
    ) -> MemoTag:
        organization = await self._organization_repository.get_active_by_id(organization_id)
        if organization is None:
            from app.organizations.exceptions import OrganizationNotFoundException

            raise OrganizationNotFoundException()

        existing = await self._tag_repository.get_by_name_and_org(data.name, organization_id)
        if existing is not None:
            raise DuplicateValueException(
                "A tag with this name already exists in the organization."
            )

        tag = MemoTag(
            organization_id=organization_id,
            name=data.name,
            color=data.color,
        )
        return await self._tag_repository.create(tag)

    async def list_tags(self, organization_id: UUID) -> list[MemoTag]:
        return await self._tag_repository.list_by_organization(organization_id)

    async def delete(self, tag_id: UUID, current_user: User) -> None:
        tag = await self._tag_repository.get(tag_id)
        if tag is None or tag.deleted_at is not None:
            raise MemoTagNotFoundException()
        await self._tag_repository.delete_soft(tag)


class MemoService:
    def __init__(
        self,
        memo_repository: MemoRepository,
        tag_repository: MemoTagRepository,
        version_repository: MemoVersionRepository,
        folder_repository: MemoFolderRepository,
        organization_repository: OrganizationRepository,
    ) -> None:
        self._memo_repository = memo_repository
        self._tag_repository = tag_repository
        self._version_repository = version_repository
        self._folder_repository = folder_repository
        self._organization_repository = organization_repository

    async def create(
        self,
        organization_id: UUID,
        data: MemoCreate,
        current_user: User,
    ) -> Memo:
        organization = await self._organization_repository.get_active_by_id(organization_id)
        if organization is None:
            from app.organizations.exceptions import OrganizationNotFoundException

            raise OrganizationNotFoundException()

        tags: list[MemoTag] = []
        if data.tag_ids:
            tags = await self._tag_repository.get_many_by_ids(data.tag_ids)

        memo = Memo(
            organization_id=organization_id,
            owner_id=current_user.id,
            folder_id=data.folder_id,
            title=data.title,
            content=data.content,
            is_pinned=data.is_pinned,
            is_favorite=data.is_favorite,
            created_by=current_user.id,
            updated_by=current_user.id,
            tags=tags,
        )
        memo = await self._memo_repository.create(memo)

        version = MemoVersion(
            memo_id=memo.id,
            version_number=1,
            content=data.content,
            created_by=current_user.id,
        )
        await self._version_repository.create(version)

        return await self._memo_repository.get_active_by_id(memo.id) or memo

    async def get(self, memo_id: UUID) -> Memo:
        memo = await self._memo_repository.get_active_by_id(memo_id)
        if memo is None:
            raise MemoNotFoundException()
        return memo

    async def update(
        self,
        memo_id: UUID,
        data: MemoUpdate,
        current_user: User,
    ) -> Memo:
        memo = await self.get(memo_id)
        update_data = data.model_dump(exclude_unset=True)

        if "tag_ids" in update_data:
            tag_ids = update_data.pop("tag_ids")
            memo.tags = await self._tag_repository.get_many_by_ids(tag_ids)

        content_changed = (
            "content" in update_data and update_data["content"] != memo.content
        )

        update_data["updated_by"] = current_user.id
        updated_memo = await self._memo_repository.update(memo, update_data)

        if content_changed:
            existing_versions = await self._version_repository.list_by_memo(updated_memo.id)
            next_version = len(existing_versions) + 1
            version = MemoVersion(
                memo_id=updated_memo.id,
                version_number=next_version,
                content=data.content,
                created_by=current_user.id,
            )
            await self._version_repository.create(version)

        return await self._memo_repository.get_active_by_id(updated_memo.id) or updated_memo

    async def delete(self, memo_id: UUID, current_user: User) -> None:
        memo = await self.get(memo_id)
        memo.updated_by = current_user.id
        await self._memo_repository.delete_soft(memo)

    async def list_memos(
        self,
        organization_id: UUID,
        pagination: PaginationParams,
        owner_id: UUID | None = None,
        folder_id: UUID | None = None,
        is_pinned: bool | None = None,
        is_favorite: bool | None = None,
        search: str | None = None,
    ) -> tuple[list[Memo], PaginationMeta]:
        return await self._memo_repository.list_by_organization(
            organization_id=organization_id,
            pagination=pagination,
            owner_id=owner_id,
            folder_id=folder_id,
            is_pinned=is_pinned,
            is_favorite=is_favorite,
            search=search,
        )

    async def pin(self, memo_id: UUID, current_user: User) -> Memo:
        memo = await self.get(memo_id)
        return await self._memo_repository.update(
            memo, {"is_pinned": True, "updated_by": current_user.id}
        )

    async def unpin(self, memo_id: UUID, current_user: User) -> Memo:
        memo = await self.get(memo_id)
        return await self._memo_repository.update(
            memo, {"is_pinned": False, "updated_by": current_user.id}
        )

    async def favorite(self, memo_id: UUID, current_user: User) -> Memo:
        memo = await self.get(memo_id)
        return await self._memo_repository.update(
            memo, {"is_favorite": True, "updated_by": current_user.id}
        )

    async def unfavorite(self, memo_id: UUID, current_user: User) -> Memo:
        memo = await self.get(memo_id)
        return await self._memo_repository.update(
            memo, {"is_favorite": False, "updated_by": current_user.id}
        )

    async def list_versions(self, memo_id: UUID) -> list[MemoVersion]:
        memo = await self.get(memo_id)
        return await self._version_repository.list_by_memo(memo.id)
