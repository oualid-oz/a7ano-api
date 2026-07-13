"""fix_timestamp_defaults_use_now_function

Revision ID: efb736949e8b
Revises: 73d266e9d519
Create Date: 2026-07-13 09:19:29.660891

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op  # noqa: E402

# revision identifiers, used by Alembic.
revision: str = "efb736949e8b"
down_revision: str | None = "73d266e9d519"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_TABLES = [
    "audit_events",
    "dm_conversation_participants",
    "dm_conversations",
    "dm_messages",
    "events",
    "memo_folders",
    "memo_tags",
    "memo_versions",
    "memos",
    "notifications",
    "organization_invitations",
    "organizations",
    "permissions",
    "project_assignments",
    "project_tags",
    "projects",
    "refresh_sessions",
    "roles",
    "tasks",
    "teams",
    "user_roles",
    "users",
    "vault_access_logs",
    "vault_categories",
    "vault_entries",
    "vault_shares",
    "vault_tags",
]

_ATTACHMENT_TABLES = ["dm_message_attachments"]


def upgrade() -> None:
    for table in _TABLES:
        op.alter_column(
            table,
            "created_at",
            server_default=sa.text("now()"),
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=False,
        )
        op.alter_column(
            table,
            "updated_at",
            server_default=sa.text("now()"),
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=False,
        )
    for table in _ATTACHMENT_TABLES:
        op.alter_column(
            table,
            "created_at",
            server_default=sa.text("now()"),
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=False,
        )


def downgrade() -> None:
    pass
