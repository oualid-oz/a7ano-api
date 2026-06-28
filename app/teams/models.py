from typing import Any
from uuid import UUID

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.models import AuditMixin, BaseModel, TimestampMixin


class Team(BaseModel, AuditMixin, TimestampMixin):
    __tablename__ = "teams"

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    organization: Mapped[Any] = relationship("Organization", lazy="selectin")
