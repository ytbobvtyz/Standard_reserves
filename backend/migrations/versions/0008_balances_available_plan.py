"""Rename available_balances.quantity to available and add plan.

Revision ID: 0008_balances_available_plan
Revises: 0007_object_erp_fields
Create Date: 2026-08-21
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0008_balances_available_plan"
down_revision: str | Sequence[str] | None = "0007_object_erp_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFICIT_VIEW_NEW = """
CREATE VIEW deficit_view AS
SELECT
    n.warehouse_code,
    o.name AS warehouse_name,
    n.product_code,
    p.name AS product_name,
    p.category,
    n.quantity AS normative_quantity,
    n.unit AS normative_unit,
    COALESCE(ab.available, 0) AS available,
    COALESCE(ab.plan, 0) AS plan,
    COALESCE(ab.unit, 'шт') AS fact_unit,
    (n.quantity - COALESCE(ab.plan, 0)) AS deficit,
    n.expiry_date,
    n.client_name,
    CASE
        WHEN (n.quantity - COALESCE(ab.plan, 0)) > 0 THEN 'warning'
        ELSE 'ok'
    END AS status
FROM normatives n
JOIN objects o ON n.warehouse_code = o.code
JOIN products p ON n.product_code = p.code
LEFT JOIN available_balances ab
    ON n.warehouse_code = ab.warehouse_code
    AND n.product_code = ab.product_code
WHERE n.deleted_at IS NULL
  AND n.expiry_date >= CURRENT_DATE
  AND (n.quantity - COALESCE(ab.plan, 0)) > 0;
"""

DEFICIT_VIEW_OLD = """
CREATE VIEW deficit_view AS
SELECT
    n.warehouse_code,
    o.name AS warehouse_name,
    n.product_code,
    p.name AS product_name,
    p.category,
    n.quantity AS normative_quantity,
    n.unit AS normative_unit,
    COALESCE(ab.quantity, 0) AS fact_quantity,
    COALESCE(ab.unit, 'шт') AS fact_unit,
    (n.quantity - COALESCE(ab.quantity, 0)) AS deficit,
    n.expiry_date,
    n.client_name,
    CASE
        WHEN (n.quantity - COALESCE(ab.quantity, 0)) > 0 THEN 'warning'
        ELSE 'ok'
    END AS status
FROM normatives n
JOIN objects o ON n.warehouse_code = o.code
JOIN products p ON n.product_code = p.code
LEFT JOIN available_balances ab
    ON n.warehouse_code = ab.warehouse_code
    AND n.product_code = ab.product_code
WHERE n.deleted_at IS NULL
  AND n.expiry_date >= CURRENT_DATE
  AND (n.quantity - COALESCE(ab.quantity, 0)) > 0;
"""


def upgrade() -> None:
    op.execute("DROP VIEW IF EXISTS deficit_view;")
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'available_balances'
                  AND column_name = 'quantity'
            ) AND NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'available_balances'
                  AND column_name = 'available'
            ) THEN
                ALTER TABLE available_balances RENAME COLUMN quantity TO available;
            END IF;
        END $$;
        """)
    op.execute("""
        ALTER TABLE available_balances
            ADD COLUMN IF NOT EXISTS plan DECIMAL(12,2) NOT NULL DEFAULT 0;
        """)
    op.execute("UPDATE available_balances SET plan = available;")
    op.execute("DROP INDEX IF EXISTS idx_available_balances_quantity;")
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_available_balances_available
            ON available_balances(available)
            WHERE available > 0;
        """)
    op.execute(DEFICIT_VIEW_NEW)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS deficit_view;")
    op.execute("DROP INDEX IF EXISTS idx_available_balances_available;")
    op.execute("ALTER TABLE available_balances DROP COLUMN IF EXISTS plan;")
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'available_balances'
                  AND column_name = 'available'
            ) AND NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'available_balances'
                  AND column_name = 'quantity'
            ) THEN
                ALTER TABLE available_balances RENAME COLUMN available TO quantity;
            END IF;
        END $$;
        """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_available_balances_quantity
            ON available_balances(quantity)
            WHERE quantity > 0;
        """)
    op.execute(DEFICIT_VIEW_OLD)
