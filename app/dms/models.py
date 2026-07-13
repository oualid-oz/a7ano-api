from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.models import Base, BaseModel, SoftDeleteMixin, TimestampMixin, UuidPrimaryKeyMixin


class Conversation(BaseModel, TimestampMixin):
    __tablename__ = "dm_conversations"

    type: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    last_message_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    creator: Mapped[Any] = relationship("User", foreign_keys=[created_by], lazy="selectin")
    participants: Mapped[list[Any]] = relationship(
        "ConversationParticipant",
        back_populates="conversation",
        lazy="selectin",
        primaryjoin="and_(Conversation.id == ConversationParticipant.conversation_id, "
        "ConversationParticipant.left_at.is_(None))",
    )


class ConversationParticipant(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "dm_conversation_participants"

    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey("dm_conversations.id"), nullable=False, index=True
    )
    member_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    team_id: Mapped[UUID | None] = mapped_column(ForeignKey("teams.id"), nullable=True, index=True)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    left_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_read_message_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("dm_messages.id"), nullable=True
    )
    last_read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_muted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        Index(
            "ix_dm_participants_conv_member",
            "conversation_id",
            "member_id",
            unique=True,
            postgresql_where=__import__("sqlalchemy").text(
                "member_id IS NOT NULL AND left_at IS NULL"
            ),
        ),
        Index(
            "ix_dm_participants_conv_team",
            "conversation_id",
            "team_id",
            unique=True,
            postgresql_where=__import__("sqlalchemy").text(
                "team_id IS NOT NULL AND left_at IS NULL"
            ),
        ),
    )

    conversation: Mapped[Any] = relationship(
        "Conversation", back_populates="participants", lazy="selectin"
    )
    member: Mapped[Any] = relationship("User", foreign_keys=[member_id], lazy="selectin")
    team: Mapped[Any] = relationship("Team", foreign_keys=[team_id], lazy="selectin")


class Message(UuidPrimaryKeyMixin, SoftDeleteMixin, Base):
    __tablename__ = "dm_messages"

    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey("dm_conversations.id"), nullable=False, index=True
    )
    sender_member_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    sender_team_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("teams.id"), nullable=True, index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    message_type: Mapped[str] = mapped_column(String(16), nullable=False, default="text")
    reply_to_message_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("dm_messages.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()"), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        onupdate=lambda: datetime.now(UTC),
    )
    is_edited: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (Index("ix_dm_messages_conv_created", "conversation_id", "created_at"),)

    sender: Mapped[Any] = relationship("User", foreign_keys=[sender_member_id], lazy="selectin")
    sender_team: Mapped[Any] = relationship("Team", foreign_keys=[sender_team_id], lazy="selectin")
    reply_to: Mapped[Any] = relationship(
        "Message", foreign_keys=[reply_to_message_id], remote_side="Message.id", lazy="selectin"
    )
    attachments: Mapped[list[Any]] = relationship(
        "MessageAttachment", back_populates="message", lazy="selectin"
    )


class MessageAttachment(UuidPrimaryKeyMixin, Base):
    __tablename__ = "dm_message_attachments"

    message_id: Mapped[UUID] = mapped_column(
        ForeignKey("dm_messages.id"), nullable=False, index=True
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    message: Mapped[Any] = relationship("Message", back_populates="attachments", lazy="selectin")
