"""add role:read to organizme admin role

Revision ID: 8991bb29a12a
Revises: b8b4a5b3ada1
Create Date: 2026-07-10 18:54:38.694700

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '8991bb29a12a'
down_revision: str | None = 'b8b4a5b3ada1'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT
            r.id,
            p.id
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.name = 'organization_admin'
          AND p.name = 'role:read'
          AND NOT EXISTS (
              SELECT 1
              FROM role_permissions rp
              WHERE rp.role_id = r.id
                AND rp.permission_id = p.id
          );
    """)


def downgrade() -> None:
    op.execute("""
        DELETE FROM role_permissions
        WHERE role_id = (
            SELECT id
            FROM roles
            WHERE name = 'organization_admin'
        )
        AND permission_id = (
            SELECT id
            FROM permissions
            WHERE name = 'role:read'
        );
    """)
