"""Add objects.long_distance and requirement formula.

Revision ID: 0015_object_long_distance
Revises: 0014_drop_rework_statuses
Create Date: 2026-08-24
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0015_object_long_distance"
down_revision: str | Sequence[str] | None = "0014_drop_rework_statuses"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFICIT_VIEW = """
CREATE VIEW deficit_view AS
SELECT
    n.warehouse_code,
    o.name AS warehouse_name,
    n.product_code,
    p.name AS product_name,
    p.category,
    n.quantity AS normative_quantity,
    n.quantity
        * CASE p.category
            WHEN 'A' THEN 1 WHEN 'B' THEN 1.5 WHEN 'C' THEN 2 ELSE 1
          END
        * CASE WHEN o.long_distance THEN 1.5 ELSE 1 END
        AS requirement,
    n.unit AS normative_unit,
    COALESCE(ab.available, 0) AS available,
    COALESCE(ab.plan, 0) AS plan,
    COALESCE(ab.unit, 'шт') AS fact_unit,
    (
        n.quantity
        * CASE p.category
            WHEN 'A' THEN 1 WHEN 'B' THEN 1.5 WHEN 'C' THEN 2 ELSE 1
          END
        * CASE WHEN o.long_distance THEN 1.5 ELSE 1 END
        - COALESCE(ab.plan, 0)
    ) AS deficit,
    n.expiry_date,
    n.client_name,
    CASE
        WHEN (
            n.quantity
            * CASE p.category
                WHEN 'A' THEN 1 WHEN 'B' THEN 1.5 WHEN 'C' THEN 2 ELSE 1
              END
            * CASE WHEN o.long_distance THEN 1.5 ELSE 1 END
            - COALESCE(ab.plan, 0)
        ) > 0 THEN 'warning'
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
  AND (
        n.quantity
        * CASE p.category
            WHEN 'A' THEN 1 WHEN 'B' THEN 1.5 WHEN 'C' THEN 2 ELSE 1
          END
        * CASE WHEN o.long_distance THEN 1.5 ELSE 1 END
        - COALESCE(ab.plan, 0)
      ) > 0;
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

CALCULATE_NORMATIVE = """
CREATE OR REPLACE FUNCTION calculate_normative(
    p_product_code INTEGER,
    p_warehouse_code INTEGER
) RETURNS DECIMAL(12,2) AS $$
DECLARE
    v_monthly_consumption DECIMAL(12,2);
    v_category CHAR(1);
    v_long_distance BOOLEAN;
    v_result DECIMAL(12,2);
BEGIN
    SELECT monthly_consumption, category
    INTO v_monthly_consumption, v_category
    FROM products
    WHERE code = p_product_code
      AND deleted_at IS NULL;

    IF v_monthly_consumption IS NULL THEN
        RETURN NULL;
    END IF;

    SELECT COALESCE(long_distance, false) INTO v_long_distance
    FROM objects
    WHERE code = p_warehouse_code
      AND deleted_at IS NULL;

    v_result := v_monthly_consumption *
        CASE WHEN v_long_distance THEN 1.5 ELSE 1 END *
        CASE v_category
            WHEN 'A' THEN 1
            WHEN 'B' THEN 1.5
            WHEN 'C' THEN 2
        END;

    RETURN v_result;
END;
$$ LANGUAGE plpgsql;
"""

CALCULATE_NORMATIVE_OLD = """
CREATE OR REPLACE FUNCTION calculate_normative(
    p_product_code INTEGER,
    p_warehouse_code INTEGER
) RETURNS DECIMAL(12,2) AS $$
DECLARE
    v_monthly_consumption DECIMAL(12,2);
    v_category CHAR(1);
    v_result DECIMAL(12,2);
BEGIN
    SELECT monthly_consumption, category
    INTO v_monthly_consumption, v_category
    FROM products
    WHERE code = p_product_code
      AND deleted_at IS NULL;

    IF v_monthly_consumption IS NULL THEN
        RETURN NULL;
    END IF;

    v_result := v_monthly_consumption * 1 *
        CASE v_category
            WHEN 'A' THEN 1
            WHEN 'B' THEN 1.5
            WHEN 'C' THEN 2
        END;

    RETURN v_result;
END;
$$ LANGUAGE plpgsql;
"""


def upgrade() -> None:
    op.execute("""
        ALTER TABLE objects
            ADD COLUMN IF NOT EXISTS long_distance BOOLEAN NOT NULL DEFAULT false;
        """)
    op.execute("DROP VIEW IF EXISTS deficit_view;")
    op.execute(DEFICIT_VIEW)
    op.execute(CALCULATE_NORMATIVE)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS deficit_view;")
    op.execute("ALTER TABLE objects DROP COLUMN IF EXISTS long_distance;")
    op.execute(DEFICIT_VIEW_OLD)
    op.execute(CALCULATE_NORMATIVE_OLD)
