from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Column, DateTime, ForeignKey, String, Table, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.models import AuditMixin, Base, BaseModel, TimestampMixin


class Project(BaseModel, AuditMixin, TimestampMixin):
    __tablename__ = "projects"

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    team_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("teams.id"), nullable=True, index=True
    )
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True)
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="medium", index=True)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    organization: Mapped[Any] = relationship("Organization", lazy="selectin")
    owner: Mapped[Any] = relationship("User", lazy="selectin", foreign_keys=[owner_id])
    tags: Mapped[list[ProjectTag]] = relationship(
        "ProjectTag",
        secondary="project_tag_assignments",
        back_populates="projects",
        lazy="selectin",
    )
    assignees: Mapped[list[ProjectAssignment]] = relationship(
        "ProjectAssignment",
        back_populates="project",
        lazy="selectin",
        primaryjoin=(
            "and_(ProjectAssignment.project_id == Project.id,"
            " ProjectAssignment.deleted_at.is_(None))"
        ),
    )

    @property
    def is_archived(self) -> bool:
        return self.archived_at is not None


class ProjectTag(BaseModel, TimestampMixin):
    __tablename__ = "project_tags"

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    color: Mapped[str | None] = mapped_column(String(16), nullable=True)

    projects: Mapped[list[Project]] = relationship(
        "Project",
        secondary="project_tag_assignments",
        back_populates="tags",
        lazy="selectin",
    )


project_tag_assignments_table = Table(
    "project_tag_assignments",
    Base.metadata,
    Column("project_id", Uuid, ForeignKey("projects.id"), primary_key=True),
    Column("tag_id", Uuid, ForeignKey("project_tags.id"), primary_key=True),
)


class ProjectAssignment(BaseModel, TimestampMixin):
    __tablename__ = "project_assignments"

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id"), nullable=False, index=True
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="member")

    project: Mapped[Any] = relationship("Project", back_populates="assignees", lazy="selectin")
    user: Mapped[Any] = relationship("User", lazy="selectin")
