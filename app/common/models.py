from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, Uuid, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        onupdate=lambda: datetime.now(UTC),
    )


class SoftDeleteMixin:
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    def soft_delete(self) -> None:
        self.deleted_at = datetime.now(UTC)

    def restore(self) -> None:
        self.deleted_at = None


class AuditMixin:
    created_by: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("users.id"), nullable=True)
    updated_by: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("users.id"), nullable=True)


class VersionMixin:
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    def bump_version(self) -> None:
        self.version += 1


class UuidPrimaryKeyMixin:
    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid4,
    )


class BaseModel(Base, UuidPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, VersionMixin):
    __abstract__ = True

    def to_dict(self) -> dict[str, Any]:
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}
