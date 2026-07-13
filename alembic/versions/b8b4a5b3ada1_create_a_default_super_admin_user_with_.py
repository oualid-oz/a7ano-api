"""create a default super_admin user with it's permissions

Revision ID: b8b4a5b3ada1
Revises: bf491961dd88
Create Date: 2026-07-09 12:05:50.619953

"""

from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa

from alembic import op
from app.core.security import hash_password

# revision identifiers, used by Alembic.
revision: str = "b8b4a5b3ada1"
down_revision: str | None = "bf491961dd88"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Default super admin credentials. Change this password after first login.
DEFAULT_ADMIN_EMAIL = "admin@example.com"
DEFAULT_ADMIN_PASSWORD = "admin123"  # noqa: S105
DEFAULT_ADMIN_FULL_NAME = "Super Admin"


def upgrade() -> None:
    connection = op.get_bind()

    # Skip if the default admin already exists.
    existing_user_id = connection.execute(
        sa.text("SELECT id FROM users WHERE email = :email AND deleted_at IS NULL"),
        {"email": DEFAULT_ADMIN_EMAIL},
    ).scalar_one_or_none()

    if existing_user_id is not None:
        return

    # Find the seeded super_admin role.
    role_id = connection.execute(
        sa.text("SELECT id FROM roles WHERE name = 'super_admin' AND deleted_at IS NULL"),
    ).scalar_one_or_none()

    if role_id is None:
        raise RuntimeError(
            "super_admin role not found. Start the application once to seed default roles and permissions."  # noqa: E501
        )

    user_id = uuid4()
    password_hash = hash_password(DEFAULT_ADMIN_PASSWORD)

    connection.execute(
        sa.text(
            """
            INSERT INTO users (
                id, email, password_hash, full_name, is_active, is_verified,
                failed_login_attempts, version, created_at, updated_at, deleted_at
            ) VALUES (
                :id, :email, :password_hash, :full_name, true, true,
                0, 0, now(), now(), NULL
            )
            """
        ),
        {
            "id": user_id,
            "email": DEFAULT_ADMIN_EMAIL,
            "password_hash": password_hash,
            "full_name": DEFAULT_ADMIN_FULL_NAME,
        },
    )

    connection.execute(
        sa.text(
            """
            INSERT INTO user_roles (
                id, user_id, role_id, organization_id, team_id, version,
                created_at, updated_at, deleted_at
            ) VALUES (
                :id, :user_id, :role_id, NULL, NULL, 0,
                now(), now(), NULL
            )
            ON CONFLICT DO NOTHING
            """
        ),
        {"id": uuid4(), "user_id": user_id, "role_id": role_id},
    )


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text(
            "DELETE FROM user_roles WHERE user_id IN (SELECT id FROM users WHERE email = :email)"
        ),
        {"email": DEFAULT_ADMIN_EMAIL},
    )
    connection.execute(
        sa.text("DELETE FROM users WHERE email = :email"),
        {"email": DEFAULT_ADMIN_EMAIL},
    )
