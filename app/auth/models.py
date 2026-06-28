from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.models import BaseModel


class RefreshSession(BaseModel):
    __tablename__ = "refresh_sessions"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True, unique=True)
    device_fingerprint: Mapped[str | None] = mapped_column(String(255), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[Any] = relationship("User", lazy="selectin")

    def is_expired(self) -> bool:
        return self.expires_at < datetime.now(UTC)

    def revoke(self) -> None:
        self.revoked_at = datetime.now(UTC)

    def is_active(self) -> bool:
        return self.revoked_at is None and not self.is_expired()
