from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Conversation
# ---------------------------------------------------------------------------


class ConversationCreate(BaseModel):
    type: str = Field(..., pattern="^(direct|group|member_team|team_team)$")
    title: str | None = Field(None, max_length=255)
    member_ids: list[UUID] = Field(default_factory=list)
    team_ids: list[UUID] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_participants(self) -> "ConversationCreate":
        total = len(self.member_ids) + len(self.team_ids)
        if self.type == "direct" and total != 1:
            raise ValueError("Direct conversations require exactly one other participant.")
        if self.type == "group" and total < 1:
            raise ValueError("Group conversations require at least one other participant.")
        if self.type == "member_team" and (len(self.member_ids) != 0 or len(self.team_ids) != 1):
            raise ValueError("member_team requires exactly one team.")
        if self.type == "team_team" and (len(self.team_ids) != 2 or len(self.member_ids) != 0):
            raise ValueError("team_team requires exactly two teams.")
        return self


class ConversationUpdate(BaseModel):
    title: str | None = Field(None, max_length=255)
    is_archived: bool | None = None
    is_muted: bool | None = None


class ParticipantResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    member_id: UUID | None
    team_id: UUID | None
    joined_at: datetime
    left_at: datetime | None
    last_read_at: datetime | None
    is_admin: bool
    is_muted: bool
    member_name: str | None = None
    member_avatar: str | None = None
    team_name: str | None = None

    model_config = {"from_attributes": True}


class MessageSummaryResponse(BaseModel):
    id: UUID
    content: str
    sender_member_id: UUID
    sender_name: str | None = None
    created_at: datetime
    is_edited: bool

    model_config = {"from_attributes": True}


class ConversationResponse(BaseModel):
    id: UUID
    type: str
    title: str | None
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    last_message_at: datetime | None
    is_archived: bool
    participants: list[ParticipantResponse] = []
    last_message: MessageSummaryResponse | None = None
    unread_count: int = 0

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Participants
# ---------------------------------------------------------------------------


class AddParticipantsRequest(BaseModel):
    member_ids: list[UUID] = Field(default_factory=list)
    team_ids: list[UUID] = Field(default_factory=list)

    @model_validator(mode="after")
    def at_least_one(self) -> "AddParticipantsRequest":
        if not self.member_ids and not self.team_ids:
            raise ValueError("Provide at least one member_id or team_id.")
        return self


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------


class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)
    message_type: str = Field("text", pattern="^(text|image|file|system)$")
    reply_to_message_id: UUID | None = None
    sender_team_id: UUID | None = None
    attachments: list["AttachmentCreate"] = Field(default_factory=list)


class AttachmentCreate(BaseModel):
    file_name: str = Field(..., max_length=255)
    file_url: str = Field(..., max_length=1024)
    mime_type: str = Field(..., max_length=128)
    file_size: int = Field(..., gt=0)


class MessageUpdate(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)


class MarkReadRequest(BaseModel):
    last_read_message_id: UUID


class AttachmentResponse(BaseModel):
    id: UUID
    message_id: UUID
    file_name: str
    file_url: str
    mime_type: str
    file_size: int
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    sender_member_id: UUID
    sender_team_id: UUID | None
    content: str
    message_type: str
    reply_to_message_id: UUID | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    is_edited: bool
    sender_name: str | None = None
    sender_avatar: str | None = None
    sender_team_name: str | None = None
    attachments: list[AttachmentResponse] = []
    reply_to: "MessageResponse | None" = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Search & unread
# ---------------------------------------------------------------------------


class MessageSearchFilters(BaseModel):
    q: str | None = None
    conversation_id: UUID | None = None
    sender_id: UUID | None = None
    team_id: UUID | None = None
    from_date: datetime | None = None
    to_date: datetime | None = None

    model_config = {"from_attributes": True}


class UnreadCountResponse(BaseModel):
    total: int
    by_conversation: dict[str, int] = {}
