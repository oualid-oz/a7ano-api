from datetime import UTC, datetime, timedelta

from sqlalchemy import Boolean, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.common.models import AuditMixin, BaseModel, TimestampMixin


class User(BaseModel, AuditMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_login_at: Mapped[datetime | None] = mapped_column(nullable=True)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(nullable=True)

    __table_args__ = (
        Index(
            "ix_users_email_active",
            "email",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    def is_locked(self) -> bool:
        if self.locked_until is None:
            return False
        return self.locked_until > datetime.now(UTC)

    def lock(self, minutes: int) -> None:
        self.locked_until = datetime.now(UTC) + timedelta(minutes=minutes)

    def unlock(self) -> None:
        self.locked_until = None
        self.failed_login_attempts = 0

    def record_failed_login(self) -> None:
        self.failed_login_attempts += 1

    def record_successful_login(self) -> None:
        self.last_login_at = datetime.now(UTC)
        self.failed_login_attempts = 0
        self.locked_until = None
