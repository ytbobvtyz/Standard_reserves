"""Create singleton sync_metadata table.

Revision ID: 0011_sync_metadata
Revises: 0010_product_gtin_parent_relax
Create Date: 2026-08-22
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0011_sync_metadata"
down_revision: str | Sequence[str] | None = "0010_product_gtin_parent_relax"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS sync_metadata (
            id INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),
            last_balances_sync_at TIMESTAMP WITH TIME ZONE,
            last_balances_sync_by UUID REFERENCES users(id),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_sync_metadata_last_balances_sync_by
            ON sync_metadata(last_balances_sync_by);
        """)
    op.execute("""
        INSERT INTO sync_metadata (id)
        VALUES (1)
        ON CONFLICT (id) DO NOTHING;
        """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_sync_metadata_last_balances_sync_by;")
    op.execute("DROP TABLE IF EXISTS sync_metadata;")
