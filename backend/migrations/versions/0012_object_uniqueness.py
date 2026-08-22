"""Relax ERP uniqueness: unique loading_point only.

Revision ID: 0012_object_uniqueness
Revises: 0011_sync_metadata
Create Date: 2026-08-22
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0012_object_uniqueness"
down_revision: str | Sequence[str] | None = "0011_sync_metadata"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE objects DROP CONSTRAINT IF EXISTS objects_erp_plant_code_key;")
    op.execute(
        "ALTER TABLE objects DROP CONSTRAINT IF EXISTS objects_erp_warehouse_code_key;"
    )
    op.execute("DROP INDEX IF EXISTS objects_erp_plant_code_key;")
    op.execute("DROP INDEX IF EXISTS objects_erp_warehouse_code_key;")
    op.execute("DROP INDEX IF EXISTS uq_objects_erp_plant_code;")
    op.execute("DROP INDEX IF EXISTS uq_objects_erp_warehouse_code;")
    op.execute("DROP INDEX IF EXISTS uq_objects_loading_point;")
    op.execute("""
        CREATE UNIQUE INDEX uq_objects_loading_point
            ON objects(loading_point)
            WHERE loading_point IS NOT NULL AND deleted_at IS NULL;
        """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_objects_loading_point;")
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS objects_erp_plant_code_key
            ON objects(erp_plant_code);
        """)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS objects_erp_warehouse_code_key
            ON objects(erp_warehouse_code);
        """)
