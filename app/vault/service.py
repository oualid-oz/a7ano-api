from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.common.schemas import PaginationMeta, PaginationParams
from app.core.config import settings
from app.core.exceptions import DuplicateValueException
from app.core.logging import get_logger
from app.notifications.service import NotificationService
from app.organizations.repository import OrganizationRepository
from app.users.models import User
from app.vault.encryption import decrypt_field, encrypt_field
from app.vault.exceptions import VaultAccessDeniedException, VaultEntryNotFoundException
from app.vault.models import VaultAccessLog, VaultCategory, VaultEntry, VaultShare, VaultTag
from app.vault.repository import (
    VaultAccessLogRepository,
    VaultCategoryRepository,
    VaultEntryRepository,
    VaultShareRepository,
    VaultTagRepository,
)
from app.vault.schemas import (
    VaultCategoryCreate,
    VaultCategoryUpdate,
    VaultEntryCreate,
    VaultEntryUpdate,
    VaultShareCreate,
    VaultTagCreate,
    VaultTagUpdate,
)

logger = get_logger(__name__)


class VaultCategoryService:
    def __init__(self, category_repo: VaultCategoryRepository) -> None:
        self._category_repo = category_repo

    async def create(
        self, org_id: UUID, data: VaultCategoryCreate, current_user: User
    ) -> VaultCategory:
        logger.info(
            "Creating vault category",
            extra={
                "org_id": str(org_id),
                "category_name": data.name,
                "user_id": str(current_user.id),
            },
        )
        category = VaultCategory(
            organization_id=org_id,
            name=data.name,
            description=data.description,
            icon=data.icon,
            created_by=current_user.id,
            updated_by=current_user.id,
        )
        return await self._category_repo.create(category)

    async def list_categories(self, org_id: UUID) -> list[VaultCategory]:
        return await self._category_repo.list_by_organization(org_id)

    async def update(
        self,
        category_id: UUID,
        org_id: UUID,
        data: VaultCategoryUpdate,
        current_user: User,
    ) -> VaultCategory:
        logger.info(
            "Updating vault category",
            extra={
                "category_id": str(category_id),
                "org_id": str(org_id),
                "user_id": str(current_user.id),
            },
        )
        category = await self._category_repo.get_or_404(category_id)
        if category.organization_id != org_id:
            logger.warning(
                "Update category denied: org mismatch",
                extra={"category_id": str(category_id), "user_id": str(current_user.id)},
            )
            raise VaultAccessDeniedException()
        update_data = data.model_dump(exclude_unset=True)
        update_data["updated_by"] = current_user.id
        logger.info(
            "Updating category fields",
            extra={"category_id": str(category_id), "fields": list(update_data.keys())},
        )
        updated = await self._category_repo.update(category, update_data)
        logger.info("Vault category updated", extra={"category_id": str(updated.id)})
        return updated

    async def delete(self, category_id: UUID, org_id: UUID, current_user: User) -> None:
        logger.info(
            "Deleting vault category",
            extra={
                "category_id": str(category_id),
                "org_id": str(org_id),
                "user_id": str(current_user.id),
            },
        )
        category = await self._category_repo.get_or_404(category_id)
        if category.organization_id != org_id:
            logger.warning(
                "Delete category denied: org mismatch", extra={"category_id": str(category_id)}
            )
            raise VaultAccessDeniedException()
        await self._category_repo.delete_soft(category)
        logger.info("Vault category deleted", extra={"category_id": str(category_id)})


class VaultTagService:
    def __init__(self, tag_repo: VaultTagRepository) -> None:
        self._tag_repo = tag_repo

    async def create(self, org_id: UUID, data: VaultTagCreate, current_user: User) -> VaultTag:
        logger.info(
            "Creating vault tag",
            extra={"org_id": str(org_id), "tag_name": data.name, "user_id": str(current_user.id)},
        )
        existing = await self._tag_repo.get_by_name_and_org(data.name, org_id)
        if existing is not None:
            raise DuplicateValueException(
                f"A tag named '{data.name}' already exists in this organization."
            )
        tag = VaultTag(
            organization_id=org_id,
            owner_id=current_user.id,
            name=data.name,
            color=data.color,
            created_by=current_user.id,
            updated_by=current_user.id,
        )
        return await self._tag_repo.create(tag)

    async def list_tags(self, org_id: UUID) -> list[VaultTag]:
        return await self._tag_repo.list_by_organization(org_id)

    async def update(
        self,
        tag_id: UUID,
        org_id: UUID,
        data: VaultTagUpdate,
        current_user: User,
    ) -> VaultTag:
        logger.info(
            "Updating vault tag",
            extra={"tag_id": str(tag_id), "org_id": str(org_id), "user_id": str(current_user.id)},
        )
        tag = await self._tag_repo.get_or_404(tag_id)
        if tag.organization_id != org_id:
            logger.warning("Update tag denied: org mismatch", extra={"tag_id": str(tag_id)})
            raise VaultAccessDeniedException()

        raw = data.model_dump(exclude_unset=True)
        if "name" in raw and raw["name"] is not None and raw["name"] != tag.name:
            existing = await self._tag_repo.get_by_name_and_org(raw["name"], org_id)
            if existing is not None and existing.id != tag_id:
                raise DuplicateValueException(
                    f"A tag named '{raw['name']}' already exists in this organization."
                )

        raw["updated_by"] = current_user.id
        updated = await self._tag_repo.update(tag, raw)
        logger.info("Vault tag updated", extra={"tag_id": str(updated.id)})
        return updated

    async def delete(self, tag_id: UUID, org_id: UUID, current_user: User) -> None:
        logger.info(
            "Deleting vault tag",
            extra={"tag_id": str(tag_id), "org_id": str(org_id), "user_id": str(current_user.id)},
        )
        tag = await self._tag_repo.get_or_404(tag_id)
        if tag.organization_id != org_id:
            logger.warning("Delete tag denied: org mismatch", extra={"tag_id": str(tag_id)})
            raise VaultAccessDeniedException()
        await self._tag_repo.delete_soft(tag)
        logger.info("Vault tag deleted", extra={"tag_id": str(tag_id)})


class VaultService:
    def __init__(
        self,
        entry_repo: VaultEntryRepository,
        category_repo: VaultCategoryRepository,
        tag_repo: VaultTagRepository,
        share_repo: VaultShareRepository,
        access_log_repo: VaultAccessLogRepository,
        org_repo: OrganizationRepository,
        notification_service: NotificationService | None = None,
    ) -> None:
        self._entry_repo = entry_repo
        self._category_repo = category_repo
        self._tag_repo = tag_repo
        self._share_repo = share_repo
        self._access_log_repo = access_log_repo
        self._org_repo = org_repo
        self._notification_service = notification_service

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def create(
        self,
        org_id: UUID,
        data: VaultEntryCreate,
        current_user: User,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> VaultEntry:
        logger.info(
            "Creating vault entry",
            extra={"org_id": str(org_id), "title": data.title, "user_id": str(current_user.id)},
        )
        org = await self._org_repo.get_active_by_id(org_id)
        if org is None:
            raise VaultAccessDeniedException()
        is_owner = org.owner_id == current_user.id
        if not is_owner:
            from sqlalchemy import select

            from app.permissions.models import UserRole

            stmt = select(UserRole).where(
                UserRole.user_id == current_user.id,
                UserRole.organization_id == org_id,
            )
            result = await self._org_repo._session.execute(stmt)
            if result.scalar_one_or_none() is None:
                raise VaultAccessDeniedException()
        master_key = settings.vault_master_key

        entry = VaultEntry(
            organization_id=org_id,
            owner_id=current_user.id,
            category_id=data.category_id,
            entry_type=data.entry_type,
            title=data.title,
            url=data.url,
            expires_at=data.expires_at,
            username_encrypted=(
                encrypt_field(data.username, master_key) if data.username is not None else None
            ),
            password_encrypted=(
                encrypt_field(data.password, master_key) if data.password is not None else None
            ),
            email_encrypted=(
                encrypt_field(data.email, master_key) if data.email is not None else None
            ),
            notes_encrypted=(
                encrypt_field(data.notes, master_key) if data.notes is not None else None
            ),
            created_by=current_user.id,
            updated_by=current_user.id,
        )

        if data.tag_ids:
            entry.tags = await self._tag_repo.get_many_by_ids(data.tag_ids)

        entry = await self._entry_repo.create(entry)
        await self._access_log_repo.create_log(entry.id, current_user.id, "create", ip, user_agent)
        return entry

    async def get_entry(
        self,
        entry_id: UUID,
        current_user: User,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> dict[str, Any]:
        logger.info(
            "Fetching vault entry",
            extra={"entry_id": str(entry_id), "user_id": str(current_user.id)},
        )
        entry = await self._entry_repo.get_active_by_id(entry_id)
        if entry is None:
            logger.warning("Vault entry not found", extra={"entry_id": str(entry_id)})
            raise VaultEntryNotFoundException()

        logger.info(
            "Calling _check_access for vault entry",
            extra={"entry_id": str(entry_id), "user_id": str(current_user.id)},
        )
        await self._check_access(entry, current_user)
        await self._entry_repo.update(entry, {"last_accessed_at": datetime.now(UTC)})
        await self._access_log_repo.create_log(entry.id, current_user.id, "view", ip, user_agent)
        logger.info("Vault entry fetched and access logged", extra={"entry_id": str(entry_id)})
        return self._decrypt_entry(entry)

    async def update(
        self,
        entry_id: UUID,
        data: VaultEntryUpdate,
        current_user: User,
    ) -> dict[str, Any]:
        logger.info(
            "Updating vault entry",
            extra={"entry_id": str(entry_id), "user_id": str(current_user.id)},
        )
        entry = await self._entry_repo.get_active_by_id(entry_id)
        if entry is None:
            raise VaultEntryNotFoundException()
        if entry.owner_id != current_user.id:
            raise VaultAccessDeniedException()

        master_key = settings.vault_master_key
        update_data: dict[str, Any] = {"updated_by": current_user.id}

        raw = data.model_dump(exclude_unset=True)
        for field in ("entry_type", "title", "url", "category_id", "expires_at"):
            if field in raw:
                update_data[field] = raw[field]

        encrypted_map = {
            "username": "username_encrypted",
            "password": "password_encrypted",
            "email": "email_encrypted",
            "notes": "notes_encrypted",
        }
        for src, dst in encrypted_map.items():
            if src in raw:
                val = raw[src]
                update_data[dst] = encrypt_field(val, master_key) if val is not None else None

        if "tag_ids" in raw and raw["tag_ids"] is not None:
            entry.tags = await self._tag_repo.get_many_by_ids(raw["tag_ids"])

        entry = await self._entry_repo.update(entry, update_data)
        await self._access_log_repo.create_log(entry.id, current_user.id, "update", None, None)
        return self._decrypt_entry(entry)

    async def delete(self, entry_id: UUID, current_user: User) -> None:
        logger.info(
            "Deleting vault entry",
            extra={"entry_id": str(entry_id), "user_id": str(current_user.id)},
        )
        entry = await self._entry_repo.get_active_by_id(entry_id)
        if entry is None:
            raise VaultEntryNotFoundException()
        if entry.owner_id != current_user.id:
            raise VaultAccessDeniedException()
        entry.updated_by = current_user.id
        await self._entry_repo.delete_soft(entry)
        await self._access_log_repo.create_log(entry.id, current_user.id, "delete", None, None)

    async def list_entries(
        self,
        current_user: User,
        pagination: PaginationParams,
        organization_id: UUID | None = None,
        entry_type: str | None = None,
        category_id: UUID | None = None,
        search: str | None = None,
    ) -> tuple[list[VaultEntry], PaginationMeta]:
        logger.info(
            "Listing vault entries",
            extra={
                "user_id": str(current_user.id),
                "org_id": str(organization_id) if organization_id else None,
                "entry_type": entry_type,
                "page": pagination.page,
            },
        )
        items, meta = await self._entry_repo.list_for_user(
            user_id=current_user.id,
            pagination=pagination,
            organization_id=organization_id,
            entry_type=entry_type,
            category_id=category_id,
            search=search,
        )
        logger.info(
            "Vault entries list response",
            extra={"user_id": str(current_user.id), "total": meta.total},
        )
        return items, meta

    # ------------------------------------------------------------------
    # Sharing
    # ------------------------------------------------------------------

    async def share(self, entry_id: UUID, data: VaultShareCreate, current_user: User) -> VaultShare:
        logger.info(
            "Sharing vault entry",
            extra={
                "entry_id": str(entry_id),
                "shared_with": str(data.shared_with_user_id),
                "user_id": str(current_user.id),
            },
        )
        entry = await self._entry_repo.get_active_by_id(entry_id)
        if entry is None:
            raise VaultEntryNotFoundException()
        if entry.owner_id != current_user.id:
            raise VaultAccessDeniedException()

        if data.shared_with_user_id is not None:
            existing = await self._share_repo.get_share(entry_id, data.shared_with_user_id)
            if existing is not None:
                raise DuplicateValueException("Entry is already shared with this user.")

        vault_share = VaultShare(
            entry_id=entry_id,
            shared_with_user_id=data.shared_with_user_id,
            shared_with_team_id=data.shared_with_team_id,
            permission=data.permission,
            expires_at=data.expires_at,
        )
        vault_share = await self._share_repo.create(vault_share)
        await self._access_log_repo.create_log(entry_id, current_user.id, "share", None, None)

        if data.shared_with_user_id is not None and self._notification_service is not None:
            logger.info(
                "Calling NotificationService.dispatch for vault share",
                extra={"entry_id": str(entry_id), "shared_with": str(data.shared_with_user_id)},
            )
            await self._notification_service.dispatch(
                user_id=data.shared_with_user_id,
                title=f"Vault entry shared with you: {entry.title}",
                body=f"{current_user.full_name} shared '{entry.title}' with you.",
                notification_type="info",
                resource_type="vault",
                resource_id=str(entry_id),
            )

        logger.info(
            "Vault share created",
            extra={"entry_id": str(entry_id), "share_id": str(vault_share.id)},
        )
        return vault_share

    async def list_shares(self, entry_id: UUID, current_user: User) -> list[VaultShare]:
        logger.info(
            "Listing vault shares",
            extra={"entry_id": str(entry_id), "user_id": str(current_user.id)},
        )
        entry = await self._entry_repo.get_active_by_id(entry_id)
        if entry is None:
            logger.warning("List shares failed: entry not found", extra={"entry_id": str(entry_id)})
            raise VaultEntryNotFoundException()
        if entry.owner_id != current_user.id:
            logger.warning(
                "List shares denied: not owner",
                extra={"entry_id": str(entry_id), "user_id": str(current_user.id)},
            )
            raise VaultAccessDeniedException()
        shares = await self._share_repo.list_by_entry(entry_id)
        logger.info("Vault shares listed", extra={"entry_id": str(entry_id), "count": len(shares)})
        return shares

    async def list_access_logs(self, entry_id: UUID, current_user: User) -> list[VaultAccessLog]:
        logger.info(
            "Listing vault access logs",
            extra={"entry_id": str(entry_id), "user_id": str(current_user.id)},
        )
        entry = await self._entry_repo.get_active_by_id(entry_id)
        if entry is None:
            logger.warning(
                "List access logs failed: entry not found", extra={"entry_id": str(entry_id)}
            )
            raise VaultEntryNotFoundException()
        if entry.owner_id != current_user.id:
            logger.warning(
                "List access logs denied: not owner",
                extra={"entry_id": str(entry_id), "user_id": str(current_user.id)},
            )
            raise VaultAccessDeniedException()
        logs = await self._access_log_repo.list_by_entry(entry_id)
        logger.info(
            "Vault access logs listed", extra={"entry_id": str(entry_id), "count": len(logs)}
        )
        return logs

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _check_access(self, entry: VaultEntry, current_user: User) -> None:
        if entry.owner_id == current_user.id:
            logger.info(
                "Access granted: owner",
                extra={"entry_id": str(entry.id), "user_id": str(current_user.id)},
            )
            return
        logger.info(
            "Calling ShareRepository.get_share for access check",
            extra={"entry_id": str(entry.id), "user_id": str(current_user.id)},
        )
        share = await self._share_repo.get_share(entry.id, current_user.id)
        if share is None:
            logger.warning(
                "Access denied: no share found",
                extra={"entry_id": str(entry.id), "user_id": str(current_user.id)},
            )
            raise VaultAccessDeniedException()
        if share.expires_at is not None and share.expires_at < datetime.now(UTC):
            logger.warning(
                "Access denied: share expired",
                extra={
                    "entry_id": str(entry.id),
                    "user_id": str(current_user.id),
                    "expired_at": str(share.expires_at),
                },
            )
            raise VaultAccessDeniedException()
        logger.info(
            "Access granted: valid share",
            extra={"entry_id": str(entry.id), "user_id": str(current_user.id)},
        )

    def _decrypt_entry(self, entry: VaultEntry) -> dict[str, Any]:
        master_key = settings.vault_master_key

        def _dec(val: str | None) -> str | None:
            return decrypt_field(val, master_key) if val is not None else None

        return {
            "id": entry.id,
            "organization_id": entry.organization_id,
            "owner_id": entry.owner_id,
            "category_id": entry.category_id,
            "category": entry.category,
            "entry_type": entry.entry_type,
            "title": entry.title,
            "username": _dec(entry.username_encrypted),
            "password": _dec(entry.password_encrypted),
            "email": _dec(entry.email_encrypted),
            "url": entry.url,
            "notes": _dec(entry.notes_encrypted),
            "expires_at": entry.expires_at,
            "last_accessed_at": entry.last_accessed_at,
            "tags": entry.tags,
            "created_at": entry.created_at,
            "updated_at": entry.updated_at,
        }
