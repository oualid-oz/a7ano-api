from typing import Any
from uuid import UUID

from fastapi import Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user
from app.core.database import get_db
from app.core.exceptions import AuthorizationException
from app.memos.exceptions import (
    MemoFolderNotFoundException,
    MemoNotFoundException,
    MemoTagNotFoundException,
)
from app.memos.models import Memo
from app.memos.repository import (
    MemoFolderRepository,
    MemoRepository,
    MemoTagRepository,
    MemoVersionRepository,
)
from app.memos.service import MemoFolderService, MemoService, MemoTagService
from app.organizations.repository import OrganizationRepository
from app.permissions.dependencies import get_authorization_service
from app.permissions.service import AuthorizationService
from app.users.models import User


def get_memo_folder_repository(
    session: AsyncSession = Depends(get_db),
) -> MemoFolderRepository:
    return MemoFolderRepository(session)


def get_memo_tag_repository(
    session: AsyncSession = Depends(get_db),
) -> MemoTagRepository:
    return MemoTagRepository(session)


def get_memo_repository(
    session: AsyncSession = Depends(get_db),
) -> MemoRepository:
    return MemoRepository(session)


def get_memo_version_repository(
    session: AsyncSession = Depends(get_db),
) -> MemoVersionRepository:
    return MemoVersionRepository(session)


def get_organization_repository(
    session: AsyncSession = Depends(get_db),
) -> OrganizationRepository:
    return OrganizationRepository(session)


def get_memo_folder_service(
    folder_repository: MemoFolderRepository = Depends(get_memo_folder_repository),
    organization_repository: OrganizationRepository = Depends(get_organization_repository),
) -> MemoFolderService:
    return MemoFolderService(folder_repository, organization_repository)


def get_memo_tag_service(
    tag_repository: MemoTagRepository = Depends(get_memo_tag_repository),
    organization_repository: OrganizationRepository = Depends(get_organization_repository),
) -> MemoTagService:
    return MemoTagService(tag_repository, organization_repository)


def get_memo_service(
    memo_repository: MemoRepository = Depends(get_memo_repository),
    tag_repository: MemoTagRepository = Depends(get_memo_tag_repository),
    version_repository: MemoVersionRepository = Depends(get_memo_version_repository),
    folder_repository: MemoFolderRepository = Depends(get_memo_folder_repository),
    organization_repository: OrganizationRepository = Depends(get_organization_repository),
) -> MemoService:
    return MemoService(
        memo_repository,
        tag_repository,
        version_repository,
        folder_repository,
        organization_repository,
    )


async def get_memo(
    memo_id: UUID = Path(...),
    repository: MemoRepository = Depends(get_memo_repository),
) -> Memo:
    memo = await repository.get_active_by_id(memo_id)
    if memo is None:
        raise MemoNotFoundException()
    return memo


def require_org_memo_permission(permission: str) -> Any:
    async def _check_permission(
        org_id: UUID,
        current_user: User = Depends(get_current_active_user),
        auth_service: AuthorizationService = Depends(get_authorization_service),
    ) -> User:
        if not await auth_service.has_permission(
            current_user.id, permission, organization_id=org_id
        ):
            raise AuthorizationException()
        return current_user

    return _check_permission


def require_memo_permission(permission: str) -> Any:
    async def _check_permission(
        memo_id: UUID = Path(...),
        current_user: User = Depends(get_current_active_user),
        auth_service: AuthorizationService = Depends(get_authorization_service),
        memo_repository: MemoRepository = Depends(get_memo_repository),
    ) -> User:
        memo = await memo_repository.get_active_by_id(memo_id)
        if memo is None:
            raise MemoNotFoundException()
        if not await auth_service.has_permission(
            current_user.id,
            permission,
            organization_id=memo.organization_id,
        ):
            raise AuthorizationException()
        return current_user

    return _check_permission


def require_memo_folder_permission(permission: str) -> Any:
    async def _check_permission(
        folder_id: UUID = Path(...),
        current_user: User = Depends(get_current_active_user),
        auth_service: AuthorizationService = Depends(get_authorization_service),
        folder_repository: MemoFolderRepository = Depends(get_memo_folder_repository),
    ) -> User:
        folder = await folder_repository.get(folder_id)
        if folder is None or folder.deleted_at is not None:
            raise MemoFolderNotFoundException()
        if not await auth_service.has_permission(
            current_user.id,
            permission,
            organization_id=folder.organization_id,
        ):
            raise AuthorizationException()
        return current_user

    return _check_permission


def require_memo_tag_permission(permission: str) -> Any:
    async def _check_permission(
        tag_id: UUID = Path(...),
        current_user: User = Depends(get_current_active_user),
        auth_service: AuthorizationService = Depends(get_authorization_service),
        tag_repository: MemoTagRepository = Depends(get_memo_tag_repository),
    ) -> User:
        tag = await tag_repository.get(tag_id)
        if tag is None or tag.deleted_at is not None:
            raise MemoTagNotFoundException()
        if not await auth_service.has_permission(
            current_user.id,
            permission,
            organization_id=tag.organization_id,
        ):
            raise AuthorizationException()
        return current_user

    return _check_permission
