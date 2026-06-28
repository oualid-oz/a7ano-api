from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.models import AuditMixin, BaseModel, TimestampMixin


class Organization(BaseModel, AuditMixin, TimestampMixin):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    owner: Mapped[Any] = relationship("User", lazy="selectin", foreign_keys=[owner_id])

    def soft_delete(self) -> None:
        self.is_active = False
        super().soft_delete()


class OrganizationInvitation(BaseModel, AuditMixin, TimestampMixin):
    __tablename__ = "organization_invitations"

    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    token: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    invited_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    role_id: Mapped[UUID] = mapped_column(ForeignKey("roles.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    accepted_by_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    organization: Mapped[Any] = relationship("Organization", lazy="selectin")
    invited_by: Mapped[Any] = relationship("User", lazy="selectin", foreign_keys=[invited_by_id])
    role: Mapped[Any] = relationship("Role", lazy="selectin")
    accepted_by: Mapped[Any] = relationship("User", lazy="selectin", foreign_keys=[accepted_by_id])

    def is_expired(self) -> bool:
        return self.expires_at < datetime.now(UTC)

    def accept(self, user_id: UUID) -> None:
        self.status = "accepted"
        self.accepted_at = datetime.now(UTC)
        self.accepted_by_id = user_id

    def revoke(self) -> None:
        self.status = "revoked"
