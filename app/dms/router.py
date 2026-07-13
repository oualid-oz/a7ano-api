from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.auth.dependencies import get_current_active_user
from app.common.dependencies import get_pagination
from app.common.responses import success_response
from app.common.schemas import PaginationParams
from app.dms.dependencies import get_dm_service
from app.dms.schemas import (
    AddParticipantsRequest,
    ConversationCreate,
    ConversationUpdate,
    MarkReadRequest,
    MessageCreate,
    MessageSearchFilters,
    MessageUpdate,
)
from app.dms.service import DMService
from app.users.models import User

router = APIRouter(prefix="/dms", tags=["direct-messages"])


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------


@router.post("/conversations", status_code=status.HTTP_201_CREATED)
async def create_conversation(
    data: ConversationCreate,
    current_user: User = Depends(get_current_active_user),
    service: DMService = Depends(get_dm_service),
) -> dict[str, Any]:
    conv = await service.create_conversation(data, current_user)
    return success_response(
        data=conv.model_dump(),
        message="Conversation created.",
    )


@router.get("/conversations")
async def list_conversations(
    conv_type: str | None = Query(None),
    search: str | None = Query(None),
    unread_only: bool = Query(False),
    archived: bool = Query(False),
    pagination: PaginationParams = Depends(get_pagination),
    current_user: User = Depends(get_current_active_user),
    service: DMService = Depends(get_dm_service),
) -> dict[str, Any]:
    items, meta = await service.list_conversations(
        current_user, pagination, conv_type, search, unread_only, archived
    )
    return success_response(
        data=[c.model_dump() for c in items],
        meta={"pagination": meta.model_dump()},
    )


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_active_user),
    service: DMService = Depends(get_dm_service),
) -> dict[str, Any]:
    conv = await service.get_conversation(conversation_id, current_user)
    return success_response(data=conv.model_dump())


@router.patch("/conversations/{conversation_id}")
async def update_conversation(
    conversation_id: UUID,
    data: ConversationUpdate,
    current_user: User = Depends(get_current_active_user),
    service: DMService = Depends(get_dm_service),
) -> dict[str, Any]:
    conv = await service.update_conversation(conversation_id, data, current_user)
    return success_response(data=conv.model_dump(), message="Conversation updated.")


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_200_OK)
async def delete_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_active_user),
    service: DMService = Depends(get_dm_service),
) -> dict[str, Any]:
    await service.delete_conversation(conversation_id, current_user)
    return success_response(message="Conversation deleted.")


# ---------------------------------------------------------------------------
# Participants
# ---------------------------------------------------------------------------


@router.post("/conversations/{conversation_id}/participants", status_code=status.HTTP_201_CREATED)
async def add_participants(
    conversation_id: UUID,
    data: AddParticipantsRequest,
    current_user: User = Depends(get_current_active_user),
    service: DMService = Depends(get_dm_service),
) -> dict[str, Any]:
    conv = await service.add_participants(conversation_id, data, current_user)
    return success_response(data=conv.model_dump(), message="Participants added.")


@router.delete(
    "/conversations/{conversation_id}/participants/{participant_id}",
    status_code=status.HTTP_200_OK,
)
async def remove_participant(
    conversation_id: UUID,
    participant_id: UUID,
    current_user: User = Depends(get_current_active_user),
    service: DMService = Depends(get_dm_service),
) -> dict[str, Any]:
    await service.remove_participant(conversation_id, participant_id, current_user)
    return success_response(message="Participant removed.")


@router.post("/conversations/{conversation_id}/leave", status_code=status.HTTP_200_OK)
async def leave_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_active_user),
    service: DMService = Depends(get_dm_service),
) -> dict[str, Any]:
    await service.leave_conversation(conversation_id, current_user)
    return success_response(message="Left conversation.")


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------


@router.get("/conversations/{conversation_id}/messages")
async def list_messages(
    conversation_id: UUID,
    before_id: UUID | None = Query(None),
    before_timestamp: datetime | None = Query(None),
    pagination: PaginationParams = Depends(get_pagination),
    current_user: User = Depends(get_current_active_user),
    service: DMService = Depends(get_dm_service),
) -> dict[str, Any]:
    msgs, meta = await service.list_messages(
        conversation_id, current_user, pagination, before_id, before_timestamp
    )
    return success_response(
        data=[m.model_dump() for m in msgs],
        meta={"pagination": meta.model_dump()},
    )


@router.post(
    "/conversations/{conversation_id}/messages", status_code=status.HTTP_201_CREATED
)
async def send_message(
    conversation_id: UUID,
    data: MessageCreate,
    current_user: User = Depends(get_current_active_user),
    service: DMService = Depends(get_dm_service),
) -> dict[str, Any]:
    msg = await service.send_message(conversation_id, data, current_user)
    return success_response(data=msg.model_dump(), message="Message sent.")


@router.patch("/messages/{message_id}")
async def edit_message(
    message_id: UUID,
    data: MessageUpdate,
    current_user: User = Depends(get_current_active_user),
    service: DMService = Depends(get_dm_service),
) -> dict[str, Any]:
    msg = await service.edit_message(message_id, data, current_user)
    return success_response(data=msg.model_dump(), message="Message updated.")


@router.delete("/messages/{message_id}", status_code=status.HTTP_200_OK)
async def delete_message(
    message_id: UUID,
    current_user: User = Depends(get_current_active_user),
    service: DMService = Depends(get_dm_service),
) -> dict[str, Any]:
    await service.delete_message(message_id, current_user)
    return success_response(message="Message deleted.")


@router.post("/conversations/{conversation_id}/read", status_code=status.HTTP_200_OK)
async def mark_read(
    conversation_id: UUID,
    data: MarkReadRequest,
    current_user: User = Depends(get_current_active_user),
    service: DMService = Depends(get_dm_service),
) -> dict[str, Any]:
    await service.mark_read(conversation_id, data, current_user)
    return success_response(message="Marked as read.")


# ---------------------------------------------------------------------------
# Search & unread
# ---------------------------------------------------------------------------


@router.get("/messages/search")
async def search_messages(
    q: str | None = Query(None),
    conversation_id: UUID | None = Query(None),
    sender_id: UUID | None = Query(None),
    team_id: UUID | None = Query(None),
    from_date: datetime | None = Query(None),
    to_date: datetime | None = Query(None),
    pagination: PaginationParams = Depends(get_pagination),
    current_user: User = Depends(get_current_active_user),
    service: DMService = Depends(get_dm_service),
) -> dict[str, Any]:
    filters = MessageSearchFilters(
        q=q,
        conversation_id=conversation_id,
        sender_id=sender_id,
        team_id=team_id,
        from_date=from_date,
        to_date=to_date,
    )
    msgs, meta = await service.search_messages(current_user, filters, pagination)
    return success_response(
        data=[m.model_dump() for m in msgs],
        meta={"pagination": meta.model_dump()},
    )


@router.get("/unread-count")
async def get_unread_count(
    current_user: User = Depends(get_current_active_user),
    service: DMService = Depends(get_dm_service),
) -> dict[str, Any]:
    result = await service.get_unread_count(current_user)
    return success_response(data=result.model_dump())
