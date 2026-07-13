from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user
from app.core.database import get_db
from app.notifications.dependencies import get_notification_service
from app.notifications.service import NotificationService
from app.organizations.repository import OrganizationRepository
from app.users.models import User
from app.vault.exceptions import VaultAccessDeniedException, VaultEntryNotFoundException
from app.vault.models import VaultEntry
from app.vault.repository import (
    VaultAccessLogRepository,
    VaultCategoryRepository,
    VaultEntryRepository,
    VaultShareRepository,
    VaultTagRepository,
)
from app.vault.service import VaultCategoryService, VaultService, VaultTagService


def get_vault_entry_repository(
    session: AsyncSession = Depends(get_db),
) -> VaultEntryRepository:
    return VaultEntryRepository(session)


def get_vault_category_repository(
    session: AsyncSession = Depends(get_db),
) -> VaultCategoryRepository:
    return VaultCategoryRepository(session)


def get_vault_tag_repository(
    session: AsyncSession = Depends(get_db),
) -> VaultTagRepository:
    return VaultTagRepository(session)


def get_vault_share_repository(
    session: AsyncSession = Depends(get_db),
) -> VaultShareRepository:
    return VaultShareRepository(session)


def get_vault_access_log_repository(
    session: AsyncSession = Depends(get_db),
) -> VaultAccessLogRepository:
    return VaultAccessLogRepository(session)


def get_organization_repository(
    session: AsyncSession = Depends(get_db),
) -> OrganizationRepository:
    return OrganizationRepository(session)


def get_vault_category_service(
    category_repo: VaultCategoryRepository = Depends(get_vault_category_repository),
) -> VaultCategoryService:
    return VaultCategoryService(category_repo)


def get_vault_tag_service(
    tag_repo: VaultTagRepository = Depends(get_vault_tag_repository),
) -> VaultTagService:
    return VaultTagService(tag_repo)


def get_vault_service(
    entry_repo: VaultEntryRepository = Depends(get_vault_entry_repository),
    category_repo: VaultCategoryRepository = Depends(get_vault_category_repository),
    tag_repo: VaultTagRepository = Depends(get_vault_tag_repository),
    share_repo: VaultShareRepository = Depends(get_vault_share_repository),
    access_log_repo: VaultAccessLogRepository = Depends(get_vault_access_log_repository),
    org_repo: OrganizationRepository = Depends(get_organization_repository),
    notification_service: NotificationService = Depends(get_notification_service),
) -> VaultService:
    return VaultService(
        entry_repo,
        category_repo,
        tag_repo,
        share_repo,
        access_log_repo,
        org_repo,
        notification_service,
    )


async def get_vault_entry(
    entry_id: UUID = Path(...),
    repository: VaultEntryRepository = Depends(get_vault_entry_repository),
) -> VaultEntry:
    entry = await repository.get_active_by_id(entry_id)
    if entry is None:
        raise VaultEntryNotFoundException()
    return entry


def require_vault_permission(permission: str) -> Any:
    async def _check_permission(
        entry_id: UUID = Path(...),
        current_user: User = Depends(get_current_active_user),
        entry_repo: VaultEntryRepository = Depends(get_vault_entry_repository),
        share_repo: VaultShareRepository = Depends(get_vault_share_repository),
    ) -> User:
        entry = await entry_repo.get_active_by_id(entry_id)
        if entry is None:
            raise VaultEntryNotFoundException()
        if entry.owner_id == current_user.id:
            return current_user
        share = await share_repo.get_share(entry_id, current_user.id)
        if share is None:
            raise VaultAccessDeniedException()
        if share.expires_at is not None and share.expires_at < datetime.now(UTC):
            raise VaultAccessDeniedException()
        if permission == "write" and share.permission != "write":
            raise VaultAccessDeniedException()
        return current_user

    return _check_permission
