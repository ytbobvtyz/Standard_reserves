"""Add ERP identification fields to objects.

Revision ID: 0007_object_erp_fields
Revises: 0006_object_admin_fields
Create Date: 2026-08-21
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0007_object_erp_fields"
down_revision: str | Sequence[str] | None = "0006_object_admin_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE objects
            ADD COLUMN IF NOT EXISTS erp_plant_code INTEGER UNIQUE;
        """)
    op.execute("""
        ALTER TABLE objects
            ADD COLUMN IF NOT EXISTS erp_warehouse_code VARCHAR(4) UNIQUE;
        """)
    op.execute("""
        ALTER TABLE objects
            ADD COLUMN IF NOT EXISTS loading_point VARCHAR(4);
        """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_objects_erp_plant_code
            ON objects(erp_plant_code)
            WHERE erp_plant_code IS NOT NULL;
        """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_objects_erp_warehouse_code
            ON objects(erp_warehouse_code)
            WHERE erp_warehouse_code IS NOT NULL;
        """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_objects_erp_warehouse_code;")
    op.execute("DROP INDEX IF EXISTS idx_objects_erp_plant_code;")
    op.execute("""
        ALTER TABLE objects
            DROP COLUMN IF EXISTS loading_point,
            DROP COLUMN IF EXISTS erp_warehouse_code,
            DROP COLUMN IF EXISTS erp_plant_code;
        """)
