from typing import Any
from uuid import UUID

from sqlalchemy import Column, DateTime, ForeignKey, String, Table, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.models import AuditMixin, Base, BaseModel, TimestampMixin

# M2M association table
vault_entry_tag_assignments = Table(
    "vault_entry_tag_assignments",
    Base.metadata,
    Column("vault_entry_id", Uuid, ForeignKey("vault_entries.id"), primary_key=True),
    Column("tag_id", Uuid, ForeignKey("vault_tags.id"), primary_key=True),
)


class VaultCategory(BaseModel, TimestampMixin, AuditMixin):
    __tablename__ = "vault_categories"

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    icon: Mapped[str | None] = mapped_column(String(64), nullable=True)


class VaultTag(BaseModel, TimestampMixin, AuditMixin):
    __tablename__ = "vault_tags"

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    color: Mapped[str | None] = mapped_column(String(16), nullable=True)


class VaultEntry(BaseModel, AuditMixin, TimestampMixin):
    __tablename__ = "vault_entries"

    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id"), nullable=True, index=True
    )
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    category_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("vault_categories.id"), nullable=True, index=True
    )
    entry_type: Mapped[str] = mapped_column(String(32), nullable=False, default="password")
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    username_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    password_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    email_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    notes_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[Any | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_accessed_at: Mapped[Any | None] = mapped_column(DateTime(timezone=True), nullable=True)

    owner: Mapped[Any] = relationship("User", foreign_keys=[owner_id], lazy="selectin")
    category: Mapped[Any] = relationship("VaultCategory", lazy="selectin")
    tags: Mapped[list[Any]] = relationship(
        "VaultTag",
        secondary=vault_entry_tag_assignments,
        lazy="selectin",
    )


class VaultShare(BaseModel):
    __tablename__ = "vault_shares"

    entry_id: Mapped[UUID] = mapped_column(
        ForeignKey("vault_entries.id"), nullable=False, index=True
    )
    shared_with_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    shared_with_team_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("teams.id"), nullable=True
    )
    permission: Mapped[str] = mapped_column(String(16), nullable=False, default="read")
    expires_at: Mapped[Any | None] = mapped_column(DateTime(timezone=True), nullable=True)

    entry: Mapped[Any] = relationship("VaultEntry", lazy="selectin")
    shared_with_user: Mapped[Any] = relationship(
        "User", foreign_keys=[shared_with_user_id], lazy="selectin"
    )


class VaultAccessLog(BaseModel):
    __tablename__ = "vault_access_logs"

    entry_id: Mapped[UUID] = mapped_column(
        ForeignKey("vault_entries.id"), nullable=False, index=True
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)

    user: Mapped[Any] = relationship("User", lazy="selectin")
