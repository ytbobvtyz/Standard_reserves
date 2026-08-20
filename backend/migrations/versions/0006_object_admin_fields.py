"""Add object admin audit fields.

Revision ID: 0006_object_admin_fields
Revises: 0005_product_admin_fields
Create Date: 2026-08-20
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0006_object_admin_fields"
down_revision: str | Sequence[str] | None = "0005_product_admin_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE objects
            ADD COLUMN IF NOT EXISTS last_modified_by UUID REFERENCES users(id);
        """)
    op.execute("""
        ALTER TABLE objects
            ADD COLUMN IF NOT EXISTS last_modified_at TIMESTAMP WITH TIME ZONE
            DEFAULT NOW();
        """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_objects_last_modified_at
            ON objects(last_modified_at);
        """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_objects_last_modified_by
            ON objects(last_modified_by);
        """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_objects_last_modified_by;")
    op.execute("DROP INDEX IF EXISTS idx_objects_last_modified_at;")
    op.execute("""
        ALTER TABLE objects
            DROP COLUMN IF EXISTS last_modified_at,
            DROP COLUMN IF EXISTS last_modified_by;
        """)
