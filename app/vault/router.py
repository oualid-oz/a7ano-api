from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from app.auth.dependencies import get_current_active_user
from app.common.dependencies import get_pagination
from app.common.responses import success_response
from app.common.schemas import PaginationParams
from app.users.models import User
from app.vault.dependencies import (
    get_vault_category_service,
    get_vault_service,
    get_vault_tag_service,
    require_vault_permission,
)
from app.vault.schemas import (
    VaultAccessLogResponse,
    VaultCategoryCreate,
    VaultCategoryResponse,
    VaultCategoryUpdate,
    VaultEntryCreate,
    VaultEntryFilters,
    VaultEntryResponse,
    VaultEntrySummaryResponse,
    VaultEntryUpdate,
    VaultShareCreate,
    VaultShareResponse,
    VaultTagCreate,
    VaultTagResponse,
    VaultTagUpdate,
)
from app.vault.service import VaultCategoryService, VaultService, VaultTagService

router = APIRouter(tags=["vault"])


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------


@router.post(
    "/organizations/{org_id}/vault/categories",
    status_code=status.HTTP_201_CREATED,
)
async def create_vault_category(
    org_id: UUID,
    data: VaultCategoryCreate,
    current_user: User = Depends(get_current_active_user),
    service: VaultCategoryService = Depends(get_vault_category_service),
) -> dict[str, Any]:
    category = await service.create(org_id, data, current_user)
    return success_response(
        data=VaultCategoryResponse.model_validate(category),
        message="Vault category created successfully.",
    )


@router.get("/organizations/{org_id}/vault/categories")
async def list_vault_categories(
    org_id: UUID,
    current_user: User = Depends(get_current_active_user),
    service: VaultCategoryService = Depends(get_vault_category_service),
) -> dict[str, Any]:
    categories = await service.list_categories(org_id)
    return success_response(
        data=[VaultCategoryResponse.model_validate(c) for c in categories],
    )


@router.patch("/organizations/{org_id}/vault/categories/{category_id}")
async def update_vault_category(
    org_id: UUID,
    category_id: UUID,
    data: VaultCategoryUpdate,
    current_user: User = Depends(get_current_active_user),
    service: VaultCategoryService = Depends(get_vault_category_service),
) -> dict[str, Any]:
    category = await service.update(category_id, org_id, data, current_user)
    return success_response(
        data=VaultCategoryResponse.model_validate(category),
        message="Vault category updated successfully.",
    )


@router.delete(
    "/organizations/{org_id}/vault/categories/{category_id}",
    status_code=status.HTTP_200_OK,
)
async def delete_vault_category(
    org_id: UUID,
    category_id: UUID,
    current_user: User = Depends(get_current_active_user),
    service: VaultCategoryService = Depends(get_vault_category_service),
) -> dict[str, Any]:
    await service.delete(category_id, org_id, current_user)
    return success_response(message="Vault category deleted successfully.")


# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------


@router.post(
    "/organizations/{org_id}/vault/tags",
    status_code=status.HTTP_201_CREATED,
)
async def create_vault_tag(
    org_id: UUID,
    data: VaultTagCreate,
    current_user: User = Depends(get_current_active_user),
    service: VaultTagService = Depends(get_vault_tag_service),
) -> dict[str, Any]:
    tag = await service.create(org_id, data, current_user)
    return success_response(
        data=VaultTagResponse.model_validate(tag),
        message="Vault tag created successfully.",
    )


@router.get("/organizations/{org_id}/vault/tags")
async def list_vault_tags(
    org_id: UUID,
    current_user: User = Depends(get_current_active_user),
    service: VaultTagService = Depends(get_vault_tag_service),
) -> dict[str, Any]:
    tags = await service.list_tags(org_id)
    return success_response(data=[VaultTagResponse.model_validate(t) for t in tags])


@router.patch("/organizations/{org_id}/vault/tags/{tag_id}")
async def update_vault_tag(
    org_id: UUID,
    tag_id: UUID,
    data: VaultTagUpdate,
    current_user: User = Depends(get_current_active_user),
    service: VaultTagService = Depends(get_vault_tag_service),
) -> dict[str, Any]:
    tag = await service.update(tag_id, org_id, data, current_user)
    return success_response(
        data=VaultTagResponse.model_validate(tag),
        message="Vault tag updated successfully.",
    )


@router.delete(
    "/organizations/{org_id}/vault/tags/{tag_id}",
    status_code=status.HTTP_200_OK,
)
async def delete_vault_tag(
    org_id: UUID,
    tag_id: UUID,
    current_user: User = Depends(get_current_active_user),
    service: VaultTagService = Depends(get_vault_tag_service),
) -> dict[str, Any]:
    await service.delete(tag_id, org_id, current_user)
    return success_response(message="Vault tag deleted successfully.")


# ---------------------------------------------------------------------------
# Entries
# ---------------------------------------------------------------------------


@router.post(
    "/organizations/{org_id}/vault",
    status_code=status.HTTP_201_CREATED,
)
async def create_vault_entry(
    org_id: UUID,
    data: VaultEntryCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    service: VaultService = Depends(get_vault_service),
) -> dict[str, Any]:
    ip = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    entry = await service.create(org_id, data, current_user, ip=ip, user_agent=user_agent)
    entry_dict = service._decrypt_entry(entry)
    return success_response(
        data=VaultEntryResponse.model_validate(entry_dict),
        message="Vault entry created successfully.",
    )


@router.get("/vault")
async def list_vault_entries(
    filters: VaultEntryFilters = Depends(),
    pagination: PaginationParams = Depends(get_pagination),
    current_user: User = Depends(get_current_active_user),
    service: VaultService = Depends(get_vault_service),
) -> dict[str, Any]:
    entries, meta = await service.list_entries(
        current_user=current_user,
        pagination=pagination,
        organization_id=filters.org_id,
        entry_type=filters.entry_type,
        category_id=filters.category_id,
        search=filters.search,
    )
    summaries = [
        VaultEntrySummaryResponse(
            id=e.id,
            organization_id=e.organization_id,
            owner_id=e.owner_id,
            category_id=e.category_id,
            category=e.category,
            entry_type=e.entry_type,
            title=e.title,
            username=None,
            email=None,
            url=e.url,
            expires_at=e.expires_at,
            last_accessed_at=e.last_accessed_at,
            tags=e.tags,
            created_at=e.created_at,
            updated_at=e.updated_at,
        )
        for e in entries
    ]
    return success_response(
        data=summaries,
        meta={"pagination": meta.model_dump()},
    )


@router.get("/vault/{entry_id}")
async def get_vault_entry(
    entry_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    _: User = Depends(require_vault_permission("read")),
    service: VaultService = Depends(get_vault_service),
) -> dict[str, Any]:
    ip = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    entry_dict = await service.get_entry(entry_id, current_user, ip=ip, user_agent=user_agent)
    return success_response(data=VaultEntryResponse.model_validate(entry_dict))


@router.patch("/vault/{entry_id}")
async def update_vault_entry(
    entry_id: UUID,
    data: VaultEntryUpdate,
    current_user: User = Depends(get_current_active_user),
    _: User = Depends(require_vault_permission("write")),
    service: VaultService = Depends(get_vault_service),
) -> dict[str, Any]:
    entry_dict = await service.update(entry_id, data, current_user)
    return success_response(
        data=VaultEntryResponse.model_validate(entry_dict),
        message="Vault entry updated successfully.",
    )


@router.delete("/vault/{entry_id}", status_code=status.HTTP_200_OK)
async def delete_vault_entry(
    entry_id: UUID,
    current_user: User = Depends(get_current_active_user),
    service: VaultService = Depends(get_vault_service),
) -> dict[str, Any]:
    await service.delete(entry_id, current_user)
    return success_response(message="Vault entry deleted successfully.")


# ---------------------------------------------------------------------------
# Sharing
# ---------------------------------------------------------------------------


@router.post("/vault/{entry_id}/shares", status_code=status.HTTP_201_CREATED)
async def share_vault_entry(
    entry_id: UUID,
    data: VaultShareCreate,
    current_user: User = Depends(get_current_active_user),
    service: VaultService = Depends(get_vault_service),
) -> dict[str, Any]:
    vault_share = await service.share(entry_id, data, current_user)
    return success_response(
        data=VaultShareResponse.model_validate(vault_share),
        message="Vault entry shared successfully.",
    )


@router.get("/vault/{entry_id}/shares")
async def list_vault_shares(
    entry_id: UUID,
    current_user: User = Depends(get_current_active_user),
    service: VaultService = Depends(get_vault_service),
) -> dict[str, Any]:
    shares = await service.list_shares(entry_id, current_user)
    return success_response(data=[VaultShareResponse.model_validate(s) for s in shares])


# ---------------------------------------------------------------------------
# Access Logs
# ---------------------------------------------------------------------------


@router.get("/vault/{entry_id}/access-logs")
async def list_vault_access_logs(
    entry_id: UUID,
    current_user: User = Depends(get_current_active_user),
    service: VaultService = Depends(get_vault_service),
) -> dict[str, Any]:
    logs = await service.list_access_logs(entry_id, current_user)
    return success_response(
        data=[VaultAccessLogResponse.model_validate(log) for log in logs],
    )
