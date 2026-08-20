"""Add execution fields for one-time logistics requests.

Revision ID: 0004_one_time_execute_fields
Revises: 0003_functions_views_triggers
Create Date: 2026-08-20
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004_one_time_execute_fields"
down_revision: str | Sequence[str] | None = "0003_functions_views_triggers"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE requests
            ADD COLUMN IF NOT EXISTS executed_by UUID REFERENCES users(id);
        """)
    op.execute("""
        ALTER TABLE requests
            ADD COLUMN IF NOT EXISTS order_number TEXT;
        """)
    op.execute("""
        ALTER TABLE requests
            ADD COLUMN IF NOT EXISTS executed_comment TEXT;
        """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE requests
            DROP COLUMN IF EXISTS executed_comment,
            DROP COLUMN IF EXISTS order_number,
            DROP COLUMN IF EXISTS executed_by;
        """)
