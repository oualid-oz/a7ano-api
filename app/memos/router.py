from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.auth.dependencies import get_current_active_user
from app.common.dependencies import get_pagination
from app.common.responses import success_response
from app.common.schemas import PaginationParams
from app.memos.dependencies import (
    get_memo,
    get_memo_folder_service,
    get_memo_service,
    get_memo_tag_service,
    require_memo_folder_permission,
    require_memo_permission,
    require_memo_tag_permission,
    require_org_memo_permission,
)
from app.memos.models import Memo
from app.memos.schemas import (
    MemoCreate,
    MemoFolderCreate,
    MemoFolderResponse,
    MemoResponse,
    MemoTagCreate,
    MemoTagResponse,
    MemoUpdate,
    MemoVersionResponse,
)
from app.memos.service import MemoFolderService, MemoService, MemoTagService
from app.users.models import User

router = APIRouter(tags=["memos"])


# ── Folders ───────────────────────────────────────────────────────────────────


@router.post(
    "/organizations/{org_id}/memos/folders",
    status_code=status.HTTP_201_CREATED,
)
async def create_memo_folder(
    org_id: UUID,
    data: MemoFolderCreate,
    current_user: User = Depends(get_current_active_user),
    _: User = Depends(require_org_memo_permission("memo:create")),
    service: MemoFolderService = Depends(get_memo_folder_service),
) -> dict[str, Any]:
    folder = await service.create(org_id, data, current_user)
    return success_response(
        data=MemoFolderResponse.model_validate(folder),
        message="Folder created successfully.",
    )


@router.get("/organizations/{org_id}/memos/folders")
async def list_memo_folders(
    org_id: UUID,
    current_user: User = Depends(get_current_active_user),
    _: User = Depends(require_org_memo_permission("memo:read")),
    service: MemoFolderService = Depends(get_memo_folder_service),
) -> dict[str, Any]:
    folders = await service.list_folders(org_id, current_user.id)
    return success_response(
        data=[MemoFolderResponse.model_validate(f) for f in folders],
    )


@router.delete("/memos/folders/{folder_id}")
async def delete_memo_folder(
    folder_id: UUID,
    current_user: User = Depends(get_current_active_user),
    _: User = Depends(require_memo_folder_permission("memo:delete")),
    service: MemoFolderService = Depends(get_memo_folder_service),
) -> dict[str, Any]:
    await service.delete(folder_id, current_user)
    return success_response(message="Folder deleted successfully.")


# ── Tags ──────────────────────────────────────────────────────────────────────


@router.post(
    "/organizations/{org_id}/memos/tags",
    status_code=status.HTTP_201_CREATED,
)
async def create_memo_tag(
    org_id: UUID,
    data: MemoTagCreate,
    current_user: User = Depends(get_current_active_user),
    _: User = Depends(require_org_memo_permission("memo:create")),
    service: MemoTagService = Depends(get_memo_tag_service),
) -> dict[str, Any]:
    tag = await service.create(org_id, data, current_user)
    return success_response(
        data=MemoTagResponse.model_validate(tag),
        message="Tag created successfully.",
    )


@router.get("/organizations/{org_id}/memos/tags")
async def list_memo_tags(
    org_id: UUID,
    _: User = Depends(require_org_memo_permission("memo:read")),
    service: MemoTagService = Depends(get_memo_tag_service),
) -> dict[str, Any]:
    tags = await service.list_tags(org_id)
    return success_response(data=[MemoTagResponse.model_validate(t) for t in tags])


@router.delete("/memos/tags/{tag_id}")
async def delete_memo_tag(
    tag_id: UUID,
    current_user: User = Depends(get_current_active_user),
    _: User = Depends(require_memo_tag_permission("memo:delete")),
    service: MemoTagService = Depends(get_memo_tag_service),
) -> dict[str, Any]:
    await service.delete(tag_id, current_user)
    return success_response(message="Tag deleted successfully.")


# ── Memos ─────────────────────────────────────────────────────────────────────


@router.post(
    "/organizations/{org_id}/memos",
    status_code=status.HTTP_201_CREATED,
)
async def create_memo(
    org_id: UUID,
    data: MemoCreate,
    current_user: User = Depends(get_current_active_user),
    _: User = Depends(require_org_memo_permission("memo:create")),
    service: MemoService = Depends(get_memo_service),
) -> dict[str, Any]:
    memo = await service.create(org_id, data, current_user)
    return success_response(
        data=MemoResponse.model_validate(memo),
        message="Memo created successfully.",
    )


@router.get("/organizations/{org_id}/memos")
async def list_memos(
    org_id: UUID,
    pagination: PaginationParams = Depends(get_pagination),
    folder_id: UUID | None = Query(None),
    is_pinned: bool | None = Query(None),
    is_favorite: bool | None = Query(None),
    search: str | None = Query(None),
    _: User = Depends(require_org_memo_permission("memo:read")),
    service: MemoService = Depends(get_memo_service),
) -> dict[str, Any]:
    items, meta = await service.list_memos(
        organization_id=org_id,
        pagination=pagination,
        folder_id=folder_id,
        is_pinned=is_pinned,
        is_favorite=is_favorite,
        search=search,
    )
    return success_response(
        data=[MemoResponse.model_validate(m) for m in items],
        meta={"pagination": meta.model_dump()},
    )


@router.get("/memos/{memo_id}")
async def get_memo_by_id(
    memo: Memo = Depends(get_memo),
    _: User = Depends(require_memo_permission("memo:read")),
) -> dict[str, Any]:
    return success_response(data=MemoResponse.model_validate(memo))


@router.patch("/memos/{memo_id}")
async def update_memo(
    memo_id: UUID,
    data: MemoUpdate,
    current_user: User = Depends(get_current_active_user),
    _: User = Depends(require_memo_permission("memo:update")),
    service: MemoService = Depends(get_memo_service),
) -> dict[str, Any]:
    memo = await service.update(memo_id, data, current_user)
    return success_response(
        data=MemoResponse.model_validate(memo),
        message="Memo updated successfully.",
    )


@router.delete("/memos/{memo_id}")
async def delete_memo(
    memo_id: UUID,
    current_user: User = Depends(get_current_active_user),
    _: User = Depends(require_memo_permission("memo:delete")),
    service: MemoService = Depends(get_memo_service),
) -> dict[str, Any]:
    await service.delete(memo_id, current_user)
    return success_response(message="Memo deleted successfully.")


@router.post("/memos/{memo_id}/pin")
async def pin_memo(
    memo_id: UUID,
    current_user: User = Depends(get_current_active_user),
    _: User = Depends(require_memo_permission("memo:update")),
    service: MemoService = Depends(get_memo_service),
) -> dict[str, Any]:
    memo = await service.pin(memo_id, current_user)
    return success_response(
        data=MemoResponse.model_validate(memo),
        message="Memo pinned successfully.",
    )


@router.delete("/memos/{memo_id}/pin")
async def unpin_memo(
    memo_id: UUID,
    current_user: User = Depends(get_current_active_user),
    _: User = Depends(require_memo_permission("memo:update")),
    service: MemoService = Depends(get_memo_service),
) -> dict[str, Any]:
    memo = await service.unpin(memo_id, current_user)
    return success_response(
        data=MemoResponse.model_validate(memo),
        message="Memo unpinned successfully.",
    )


@router.post("/memos/{memo_id}/favorite")
async def favorite_memo(
    memo_id: UUID,
    current_user: User = Depends(get_current_active_user),
    _: User = Depends(require_memo_permission("memo:update")),
    service: MemoService = Depends(get_memo_service),
) -> dict[str, Any]:
    memo = await service.favorite(memo_id, current_user)
    return success_response(
        data=MemoResponse.model_validate(memo),
        message="Memo favorited successfully.",
    )


@router.delete("/memos/{memo_id}/favorite")
async def unfavorite_memo(
    memo_id: UUID,
    current_user: User = Depends(get_current_active_user),
    _: User = Depends(require_memo_permission("memo:update")),
    service: MemoService = Depends(get_memo_service),
) -> dict[str, Any]:
    memo = await service.unfavorite(memo_id, current_user)
    return success_response(
        data=MemoResponse.model_validate(memo),
        message="Memo unfavorited successfully.",
    )


@router.get("/memos/{memo_id}/versions")
async def list_memo_versions(
    memo_id: UUID,
    _: User = Depends(require_memo_permission("memo:read")),
    service: MemoService = Depends(get_memo_service),
) -> dict[str, Any]:
    versions = await service.list_versions(memo_id)
    return success_response(
        data=[MemoVersionResponse.model_validate(v) for v in versions],
    )
