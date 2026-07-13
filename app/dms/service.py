from datetime import UTC, datetime
from uuid import UUID

from app.common.schemas import PaginationMeta, PaginationParams
from app.core.logging import get_logger
from app.dms.exceptions import (
    CannotLeaveDirectConversationException,
    ConversationAccessDeniedException,
    ConversationNotFoundException,
    DuplicateDirectConversationException,
    MessageNotFoundException,
    NotConversationAdminException,
)
from app.dms.models import (
    Conversation,
    ConversationParticipant,
    Message,
    MessageAttachment,
)
from app.dms.repository import (
    ConversationRepository,
    MessageRepository,
    ParticipantRepository,
)
from app.dms.schemas import (
    AddParticipantsRequest,
    ConversationCreate,
    ConversationResponse,
    ConversationUpdate,
    MarkReadRequest,
    MessageCreate,
    MessageResponse,
    MessageSearchFilters,
    MessageSummaryResponse,
    MessageUpdate,
    ParticipantResponse,
    UnreadCountResponse,
)
from app.users.models import User

logger = get_logger(__name__)


def _build_participant_response(p: ConversationParticipant) -> ParticipantResponse:
    return ParticipantResponse(
        id=p.id,
        conversation_id=p.conversation_id,
        member_id=p.member_id,
        team_id=p.team_id,
        joined_at=p.joined_at,
        left_at=p.left_at,
        last_read_at=p.last_read_at,
        is_admin=p.is_admin,
        is_muted=p.is_muted,
        member_name=p.member.full_name if p.member else None,
        member_avatar=p.member.avatar_url if p.member else None,
        team_name=p.team.name if p.team else None,
    )


def _build_message_response(msg: Message) -> MessageResponse:
    reply = None
    if msg.reply_to and msg.reply_to.deleted_at is None:
        reply = MessageResponse(
            id=msg.reply_to.id,
            conversation_id=msg.reply_to.conversation_id,
            sender_member_id=msg.reply_to.sender_member_id,
            sender_team_id=msg.reply_to.sender_team_id,
            content=msg.reply_to.content,
            message_type=msg.reply_to.message_type,
            reply_to_message_id=msg.reply_to.reply_to_message_id,
            created_at=msg.reply_to.created_at,
            updated_at=msg.reply_to.updated_at,
            deleted_at=msg.reply_to.deleted_at,
            is_edited=msg.reply_to.is_edited,
            sender_name=msg.reply_to.sender.full_name if msg.reply_to.sender else None,
        )
    return MessageResponse(
        id=msg.id,
        conversation_id=msg.conversation_id,
        sender_member_id=msg.sender_member_id,
        sender_team_id=msg.sender_team_id,
        content=msg.content if msg.deleted_at is None else "[Message deleted]",
        message_type=msg.message_type,
        reply_to_message_id=msg.reply_to_message_id,
        created_at=msg.created_at,
        updated_at=msg.updated_at,
        deleted_at=msg.deleted_at,
        is_edited=msg.is_edited,
        sender_name=msg.sender.full_name if msg.sender else None,
        sender_avatar=msg.sender.avatar_url if msg.sender else None,
        sender_team_name=msg.sender_team.name if msg.sender_team else None,
        attachments=[
            {
                "id": a.id,
                "message_id": a.message_id,
                "file_name": a.file_name,
                "file_url": a.file_url,
                "mime_type": a.mime_type,
                "file_size": a.file_size,
                "created_at": a.created_at,
            }
            for a in (msg.attachments or [])
        ],
        reply_to=reply,
    )


class DMService:
    def __init__(
        self,
        conv_repo: ConversationRepository,
        part_repo: ParticipantRepository,
        msg_repo: MessageRepository,
    ) -> None:
        self._conv_repo = conv_repo
        self._part_repo = part_repo
        self._msg_repo = msg_repo

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _require_participant(
        self, conversation_id: UUID, user_id: UUID
    ) -> ConversationParticipant:
        p = await self._part_repo.get_member_participant(conversation_id, user_id)
        if p is None:
            raise ConversationAccessDeniedException()
        return p

    async def _require_conversation(self, conversation_id: UUID) -> Conversation:
        conv = await self._conv_repo.get_by_id(conversation_id)
        if conv is None:
            raise ConversationNotFoundException()
        return conv

    async def _build_conv_response(
        self, conv: Conversation, user_id: UUID
    ) -> ConversationResponse:
        participants = await self._part_repo.list_by_conversation(conv.id)
        last_msg = await self._msg_repo.get_latest_in_conversation(conv.id)
        unread = await self._part_repo.count_unread(conv.id, user_id)

        last_msg_summary = None
        if last_msg:
            last_msg_summary = MessageSummaryResponse(
                id=last_msg.id,
                content=last_msg.content,
                sender_member_id=last_msg.sender_member_id,
                sender_name=last_msg.sender.full_name if last_msg.sender else None,
                created_at=last_msg.created_at,
                is_edited=last_msg.is_edited,
            )

        return ConversationResponse(
            id=conv.id,
            type=conv.type,
            title=conv.title,
            created_by=conv.created_by,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            last_message_at=conv.last_message_at,
            is_archived=conv.is_archived,
            participants=[_build_participant_response(p) for p in participants],
            last_message=last_msg_summary,
            unread_count=unread,
        )

    # ------------------------------------------------------------------
    # Conversations
    # ------------------------------------------------------------------

    async def create_conversation(
        self, data: ConversationCreate, current_user: User
    ) -> ConversationResponse:
        logger.info(
            "Creating conversation",
            extra={"type": data.type, "user_id": str(current_user.id)},
        )

        if data.type == "direct":
            other_id = data.member_ids[0]
            existing = await self._conv_repo.find_direct(current_user.id, other_id)
            if existing:
                raise DuplicateDirectConversationException()

        conv = Conversation(
            type=data.type,
            title=data.title,
            created_by=current_user.id,
        )
        conv = await self._conv_repo.create(conv)

        creator_p = ConversationParticipant(
            conversation_id=conv.id,
            member_id=current_user.id,
            is_admin=True,
        )
        await self._part_repo.create(creator_p)

        for mid in data.member_ids:
            if mid == current_user.id:
                continue
            p = ConversationParticipant(
                conversation_id=conv.id,
                member_id=mid,
                is_admin=False,
            )
            await self._part_repo.create(p)

        for tid in data.team_ids:
            p = ConversationParticipant(
                conversation_id=conv.id,
                team_id=tid,
                is_admin=False,
            )
            await self._part_repo.create(p)

        logger.info("Conversation created", extra={"conversation_id": str(conv.id)})
        return await self._build_conv_response(conv, current_user.id)

    async def list_conversations(
        self,
        current_user: User,
        pagination: PaginationParams,
        conv_type: str | None = None,
        search: str | None = None,
        unread_only: bool = False,
        archived: bool = False,
    ) -> tuple[list[ConversationResponse], PaginationMeta]:
        convs, meta = await self._conv_repo.list_for_user(
            current_user.id, pagination, conv_type, search, unread_only, archived
        )
        responses = []
        for conv in convs:
            r = await self._build_conv_response(conv, current_user.id)
            if unread_only and r.unread_count == 0:
                continue
            responses.append(r)
        return responses, meta

    async def get_conversation(
        self, conversation_id: UUID, current_user: User
    ) -> ConversationResponse:
        conv = await self._require_conversation(conversation_id)
        await self._require_participant(conversation_id, current_user.id)
        return await self._build_conv_response(conv, current_user.id)

    async def update_conversation(
        self, conversation_id: UUID, data: ConversationUpdate, current_user: User
    ) -> ConversationResponse:
        conv = await self._require_conversation(conversation_id)
        p = await self._require_participant(conversation_id, current_user.id)

        update_data: dict = {}
        if data.title is not None:
            if not p.is_admin:
                raise NotConversationAdminException()
            update_data["title"] = data.title
        if data.is_archived is not None:
            update_data["is_archived"] = data.is_archived
        if data.is_muted is not None:
            await self._part_repo.update(p, {"is_muted": data.is_muted})

        if update_data:
            conv = await self._conv_repo.update(conv, update_data)

        return await self._build_conv_response(conv, current_user.id)

    async def delete_conversation(
        self, conversation_id: UUID, current_user: User
    ) -> None:
        conv = await self._require_conversation(conversation_id)
        p = await self._require_participant(conversation_id, current_user.id)
        if not p.is_admin:
            raise NotConversationAdminException()
        await self._conv_repo.soft_delete(conv)

    # ------------------------------------------------------------------
    # Participants
    # ------------------------------------------------------------------

    async def add_participants(
        self, conversation_id: UUID, data: AddParticipantsRequest, current_user: User
    ) -> ConversationResponse:
        conv = await self._require_conversation(conversation_id)
        p = await self._require_participant(conversation_id, current_user.id)
        if not p.is_admin:
            raise NotConversationAdminException()

        for mid in data.member_ids:
            existing = await self._part_repo.get_member_participant(conversation_id, mid)
            if existing is None:
                new_p = ConversationParticipant(
                    conversation_id=conversation_id, member_id=mid, is_admin=False
                )
                await self._part_repo.create(new_p)

        for tid in data.team_ids:
            new_p = ConversationParticipant(
                conversation_id=conversation_id, team_id=tid, is_admin=False
            )
            await self._part_repo.create(new_p)

        return await self._build_conv_response(conv, current_user.id)

    async def remove_participant(
        self, conversation_id: UUID, participant_id: UUID, current_user: User
    ) -> None:
        await self._require_conversation(conversation_id)
        requester = await self._require_participant(conversation_id, current_user.id)
        target = await self._part_repo.get_by_id(participant_id)
        if target is None or target.conversation_id != conversation_id:
            raise ConversationNotFoundException()
        if target.member_id != current_user.id and not requester.is_admin:
            raise NotConversationAdminException()
        await self._part_repo.mark_left(target)

    async def leave_conversation(
        self, conversation_id: UUID, current_user: User
    ) -> None:
        conv = await self._require_conversation(conversation_id)
        if conv.type == "direct":
            raise CannotLeaveDirectConversationException()
        p = await self._require_participant(conversation_id, current_user.id)
        await self._part_repo.mark_left(p)

    # ------------------------------------------------------------------
    # Messages
    # ------------------------------------------------------------------

    async def list_messages(
        self,
        conversation_id: UUID,
        current_user: User,
        pagination: PaginationParams,
        before_id: UUID | None = None,
        before_timestamp: datetime | None = None,
    ) -> tuple[list[MessageResponse], PaginationMeta]:
        await self._require_conversation(conversation_id)
        await self._require_participant(conversation_id, current_user.id)
        msgs, meta = await self._msg_repo.list_by_conversation(
            conversation_id, pagination, before_id, before_timestamp
        )
        return [_build_message_response(m) for m in msgs], meta

    async def send_message(
        self, conversation_id: UUID, data: MessageCreate, current_user: User
    ) -> MessageResponse:
        conv = await self._require_conversation(conversation_id)
        await self._require_participant(conversation_id, current_user.id)

        logger.info(
            "Sending message",
            extra={"conversation_id": str(conversation_id), "user_id": str(current_user.id)},
        )

        msg = Message(
            conversation_id=conversation_id,
            sender_member_id=current_user.id,
            sender_team_id=data.sender_team_id,
            content=data.content,
            message_type=data.message_type,
            reply_to_message_id=data.reply_to_message_id,
        )
        msg = await self._msg_repo.create(msg)

        for att in data.attachments:
            attachment = MessageAttachment(
                message_id=msg.id,
                file_name=att.file_name,
                file_url=att.file_url,
                mime_type=att.mime_type,
                file_size=att.file_size,
            )
            self._msg_repo._session.add(attachment)

        await self._conv_repo.update(conv, {"last_message_at": datetime.now(UTC)})
        msg = await self._msg_repo.get_by_id(msg.id)
        return _build_message_response(msg)  # type: ignore[arg-type]

    async def edit_message(
        self, message_id: UUID, data: MessageUpdate, current_user: User
    ) -> MessageResponse:
        msg = await self._msg_repo.get_by_id(message_id)
        if msg is None or msg.deleted_at is not None:
            raise MessageNotFoundException()
        await self._require_participant(msg.conversation_id, current_user.id)
        if msg.sender_member_id != current_user.id:
            raise ConversationAccessDeniedException()
        msg = await self._msg_repo.update(
            msg, {"content": data.content, "is_edited": True}
        )
        return _build_message_response(msg)

    async def delete_message(
        self, message_id: UUID, current_user: User
    ) -> None:
        msg = await self._msg_repo.get_by_id(message_id)
        if msg is None or msg.deleted_at is not None:
            raise MessageNotFoundException()
        p = await self._require_participant(msg.conversation_id, current_user.id)
        if msg.sender_member_id != current_user.id and not p.is_admin:
            raise ConversationAccessDeniedException()
        await self._msg_repo.soft_delete(msg)

    async def mark_read(
        self, conversation_id: UUID, data: MarkReadRequest, current_user: User
    ) -> None:
        await self._require_conversation(conversation_id)
        p = await self._require_participant(conversation_id, current_user.id)
        await self._part_repo.update(
            p,
            {
                "last_read_message_id": data.last_read_message_id,
                "last_read_at": datetime.now(UTC),
            },
        )

    # ------------------------------------------------------------------
    # Search & unread
    # ------------------------------------------------------------------

    async def search_messages(
        self,
        current_user: User,
        filters: MessageSearchFilters,
        pagination: PaginationParams,
    ) -> tuple[list[MessageResponse], PaginationMeta]:
        msgs, meta = await self._msg_repo.search(
            user_id=current_user.id,
            q=filters.q,
            conversation_id=filters.conversation_id,
            sender_id=filters.sender_id,
            team_id=filters.team_id,
            from_date=filters.from_date,
            to_date=filters.to_date,
            pagination=pagination,
        )
        return [_build_message_response(m) for m in msgs], meta

    async def get_unread_count(self, current_user: User) -> UnreadCountResponse:
        by_conv = await self._msg_repo.count_unread_all(current_user.id)
        total = sum(by_conv.values())
        return UnreadCountResponse(total=total, by_conversation=by_conv)
