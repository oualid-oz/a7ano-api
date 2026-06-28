from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, Column, ForeignKey, Index, String, Table, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.models import Base, BaseModel, TimestampMixin


class Permission(BaseModel, TimestampMixin):
    __tablename__ = "permissions"

    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    resource: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)


class Role(BaseModel, TimestampMixin):
    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    permissions: Mapped[list[Permission]] = relationship(
        "Permission",
        secondary="role_permissions",
        back_populates="roles",
        lazy="selectin",
    )


role_permissions_table = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", Uuid, ForeignKey("roles.id"), primary_key=True),
    Column("permission_id", Uuid, ForeignKey("permissions.id"), primary_key=True),
)


Permission.roles = relationship(
    "Role",
    secondary=role_permissions_table,
    back_populates="permissions",
)


class UserRole(BaseModel, TimestampMixin):
    __tablename__ = "user_roles"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    role_id: Mapped[UUID] = mapped_column(ForeignKey("roles.id"), nullable=False, index=True)
    organization_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    team_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True, index=True)

    __table_args__ = (
        Index(
            "ix_user_roles_scope",
            "user_id",
            "role_id",
            "organization_id",
            "team_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    role: Mapped[Any] = relationship("Role", lazy="selectin")

    @property
    def role_name(self) -> str:
        return str(self.role.name)
