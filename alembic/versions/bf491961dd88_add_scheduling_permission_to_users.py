"""add scheduling permission to users

Revision ID: bf491961dd88
Revises: 1fc8adf6257e
Create Date: 2026-07-07 15:09:47.522471

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "bf491961dd88"
down_revision: str | None = "1fc8adf6257e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade():
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT
            '0c7cca0f-92af-4348-be92-a493232f0de0',
            id
        FROM permissions
        WHERE resource = 'scheduling'
        ON CONFLICT DO NOTHING;
    """)


def downgrade():
    op.execute("""
        DELETE FROM role_permissions
        WHERE role_id = '0c7cca0f-92af-4348-be92-a493232f0de0'
          AND permission_id = (
              SELECT id
              FROM permissions
              WHERE resource = 'scheduling'
          );
    """)
