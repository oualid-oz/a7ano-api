from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.models import AuditMixin, BaseModel, TimestampMixin


class Task(BaseModel, AuditMixin, TimestampMixin):
    __tablename__ = "tasks"

    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="todo", index=True)
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="medium", index=True)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    assignee_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )

    project: Mapped[Any] = relationship("Project", lazy="selectin")
    assignee: Mapped[Any] = relationship("User", lazy="selectin", foreign_keys=[assignee_id])
