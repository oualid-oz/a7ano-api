from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.schemas import PaginationMeta, PaginationParams
from app.dms.models import (
    Conversation,
    ConversationParticipant,
    Message,
)


class ConversationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, obj: Conversation) -> Conversation:
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    async def get_by_id(self, conversation_id: UUID) -> Conversation | None:
        stmt = select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def update(self, obj: Conversation, data: dict[str, Any]) -> Conversation:
        for key, value in data.items():
            if hasattr(obj, key):
                setattr(obj, key, value)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    async def soft_delete(self, obj: Conversation) -> None:
        obj.deleted_at = datetime.now(UTC)
        await self._session.flush()

    async def find_direct(self, user_a: UUID, user_b: UUID) -> Conversation | None:
        p1 = select(ConversationParticipant.conversation_id).where(
            ConversationParticipant.member_id == user_a,
            ConversationParticipant.left_at.is_(None),
        )
        p2 = select(ConversationParticipant.conversation_id).where(
            ConversationParticipant.member_id == user_b,
            ConversationParticipant.left_at.is_(None),
        )
        stmt = select(Conversation).where(
            Conversation.type == "direct",
            Conversation.deleted_at.is_(None),
            Conversation.id.in_(p1),
            Conversation.id.in_(p2),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_user(
        self,
        user_id: UUID,
        pagination: PaginationParams,
        conv_type: str | None = None,
        search: str | None = None,
        unread_only: bool = False,
        archived: bool = False,
    ) -> tuple[list[Conversation], PaginationMeta]:
        participant_conv_ids = select(ConversationParticipant.conversation_id).where(
            ConversationParticipant.member_id == user_id,
            ConversationParticipant.left_at.is_(None),
        )

        stmt = select(Conversation).where(
            Conversation.deleted_at.is_(None),
            Conversation.id.in_(participant_conv_ids),
            Conversation.is_archived == archived,
        )

        if conv_type:
            stmt = stmt.where(Conversation.type == conv_type)
        if search:
            stmt = stmt.where(Conversation.title.ilike(f"%{search}%"))

        stmt = stmt.order_by(
            desc(Conversation.last_message_at.is_(None)),
            desc(Conversation.last_message_at),
            desc(Conversation.created_at),
        )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self._session.execute(count_stmt)).scalar_one()

        offset = (pagination.page - 1) * pagination.page_size
        stmt = stmt.offset(offset).limit(pagination.page_size)
        items = list((await self._session.execute(stmt)).scalars().all())

        pages = (total + pagination.page_size - 1) // pagination.page_size
        meta = PaginationMeta(
            page=pagination.page, page_size=pagination.page_size, total=total, pages=pages or 1
        )
        return items, meta


class ParticipantRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, obj: ConversationParticipant) -> ConversationParticipant:
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    async def get_by_id(self, participant_id: UUID) -> ConversationParticipant | None:
        return await self._session.get(ConversationParticipant, participant_id)

    async def get_member_participant(
        self, conversation_id: UUID, user_id: UUID
    ) -> ConversationParticipant | None:
        stmt = select(ConversationParticipant).where(
            ConversationParticipant.conversation_id == conversation_id,
            ConversationParticipant.member_id == user_id,
            ConversationParticipant.left_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_conversation(self, conversation_id: UUID) -> list[ConversationParticipant]:
        stmt = select(ConversationParticipant).where(
            ConversationParticipant.conversation_id == conversation_id,
            ConversationParticipant.left_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update(
        self, obj: ConversationParticipant, data: dict[str, Any]
    ) -> ConversationParticipant:
        for key, value in data.items():
            if hasattr(obj, key):
                setattr(obj, key, value)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    async def mark_left(self, obj: ConversationParticipant) -> None:
        obj.left_at = datetime.now(UTC)
        await self._session.flush()

    async def count_unread(self, conversation_id: UUID, user_id: UUID) -> int:
        participant = await self.get_member_participant(conversation_id, user_id)
        if participant is None:
            return 0
        stmt = select(func.count(Message.id)).where(
            Message.conversation_id == conversation_id,
            Message.deleted_at.is_(None),
        )
        if participant.last_read_message_id is not None:
            last_read_msg = await self._session.get(Message, participant.last_read_message_id)
            if last_read_msg:
                stmt = stmt.where(Message.created_at > last_read_msg.created_at)
        result = await self._session.execute(stmt)
        return result.scalar_one()


class MessageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, obj: Message) -> Message:
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    async def get_by_id(self, message_id: UUID) -> Message | None:
        stmt = (
            select(Message)
            .where(Message.id == message_id)
            .options(
                selectinload(Message.attachments),
                selectinload(Message.reply_to),
                selectinload(Message.sender),
                selectinload(Message.sender_team),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def update(self, obj: Message, data: dict[str, Any]) -> Message:
        for key, value in data.items():
            if hasattr(obj, key):
                setattr(obj, key, value)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    async def soft_delete(self, obj: Message) -> None:
        obj.deleted_at = datetime.now(UTC)
        await self._session.flush()

    async def list_by_conversation(
        self,
        conversation_id: UUID,
        pagination: PaginationParams,
        before_id: UUID | None = None,
        before_timestamp: datetime | None = None,
    ) -> tuple[list[Message], PaginationMeta]:
        stmt = (
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.deleted_at.is_(None),
            )
            .options(
                selectinload(Message.attachments),
                selectinload(Message.reply_to),
                selectinload(Message.sender),
                selectinload(Message.sender_team),
            )
        )

        if before_id is not None:
            ref_msg = await self.get_by_id(before_id)
            if ref_msg:
                stmt = stmt.where(Message.created_at < ref_msg.created_at)
        elif before_timestamp is not None:
            stmt = stmt.where(Message.created_at < before_timestamp)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self._session.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(desc(Message.created_at)).limit(pagination.page_size)
        items = list((await self._session.execute(stmt)).scalars().all())
        items.reverse()

        pages = max(1, (total + pagination.page_size - 1) // pagination.page_size)
        meta = PaginationMeta(
            page=pagination.page, page_size=pagination.page_size, total=total, pages=pages
        )
        return items, meta

    async def get_latest_in_conversation(self, conversation_id: UUID) -> Message | None:
        stmt = (
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.deleted_at.is_(None),
            )
            .order_by(desc(Message.created_at))
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def search(
        self,
        user_id: UUID,
        q: str | None = None,
        conversation_id: UUID | None = None,
        sender_id: UUID | None = None,
        team_id: UUID | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        pagination: PaginationParams | None = None,
    ) -> tuple[list[Message], PaginationMeta]:
        accessible_conv_ids = select(ConversationParticipant.conversation_id).where(
            ConversationParticipant.member_id == user_id,
            ConversationParticipant.left_at.is_(None),
        )

        stmt = select(Message).where(
            Message.deleted_at.is_(None),
            Message.conversation_id.in_(accessible_conv_ids),
        )

        if q:
            stmt = stmt.where(Message.content.ilike(f"%{q}%"))
        if conversation_id:
            stmt = stmt.where(Message.conversation_id == conversation_id)
        if sender_id:
            stmt = stmt.where(Message.sender_member_id == sender_id)
        if team_id:
            stmt = stmt.where(Message.sender_team_id == team_id)
        if from_date:
            stmt = stmt.where(Message.created_at >= from_date)
        if to_date:
            stmt = stmt.where(Message.created_at <= to_date)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self._session.execute(count_stmt)).scalar_one()

        page = pagination or PaginationParams()
        stmt = stmt.order_by(desc(Message.created_at))
        offset = (page.page - 1) * page.page_size
        stmt = stmt.offset(offset).limit(page.page_size)
        items = list((await self._session.execute(stmt)).scalars().all())

        pages = max(1, (total + page.page_size - 1) // page.page_size)
        meta = PaginationMeta(page=page.page, page_size=page.page_size, total=total, pages=pages)
        return items, meta

    async def count_unread_all(self, user_id: UUID) -> dict[str, int]:
        participant_rows_stmt = select(ConversationParticipant).where(
            ConversationParticipant.member_id == user_id,
            ConversationParticipant.left_at.is_(None),
        )
        participants = list((await self._session.execute(participant_rows_stmt)).scalars().all())

        result: dict[str, int] = {}
        for p in participants:
            count_stmt = select(func.count(Message.id)).where(
                Message.conversation_id == p.conversation_id,
                Message.deleted_at.is_(None),
            )
            if p.last_read_message_id is not None:
                ref = await self.get_by_id(p.last_read_message_id)
                if ref:
                    count_stmt = count_stmt.where(Message.created_at > ref.created_at)
            count = (await self._session.execute(count_stmt)).scalar_one()
            result[str(p.conversation_id)] = count

        return result
