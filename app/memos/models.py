from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Table, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.models import AuditMixin, Base, BaseModel, TimestampMixin

memo_tag_assignments = Table(
    "memo_tag_assignments",
    Base.metadata,
    Column("memo_id", Uuid, ForeignKey("memos.id"), primary_key=True),
    Column("tag_id", Uuid, ForeignKey("memo_tags.id"), primary_key=True),
)


class MemoFolder(BaseModel, TimestampMixin):
    __tablename__ = "memo_folders"

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("memo_folders.id"), nullable=True
    )

    organization: Mapped[Any] = relationship("Organization", lazy="selectin")
    owner: Mapped[Any] = relationship("User", lazy="selectin")
    parent: Mapped[Any] = relationship(
        "MemoFolder", remote_side="MemoFolder.id", lazy="select"
    )


class MemoTag(BaseModel, TimestampMixin):
    __tablename__ = "memo_tags"

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    color: Mapped[str | None] = mapped_column(String(16), nullable=True)


class Memo(BaseModel, AuditMixin, TimestampMixin):
    __tablename__ = "memos"

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    folder_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("memo_folders.id"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_favorite: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    organization: Mapped[Any] = relationship(
        "Organization", foreign_keys=[organization_id], lazy="selectin"
    )
    owner: Mapped[Any] = relationship("User", foreign_keys=[owner_id], lazy="selectin")
    folder: Mapped[Any] = relationship(
        "MemoFolder", foreign_keys=[folder_id], lazy="selectin"
    )
    tags: Mapped[list[MemoTag]] = relationship(
        MemoTag,
        secondary=memo_tag_assignments,
        lazy="selectin",
    )
    versions: Mapped[Any] = relationship(
        "MemoVersion",
        back_populates="memo",
        lazy="select",
        order_by="MemoVersion.version_number.asc()",
    )


class MemoVersion(BaseModel, TimestampMixin):
    __tablename__ = "memo_versions"

    memo_id: Mapped[UUID] = mapped_column(
        ForeignKey("memos.id"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=True
    )

    memo: Mapped[Any] = relationship("Memo", back_populates="versions", lazy="selectin")
