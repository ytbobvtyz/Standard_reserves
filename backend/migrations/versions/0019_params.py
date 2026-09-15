"""Create singleton params table and use it in SQL formulas.

Revision ID: 0019_params
Revises: 0018_drop_normative_trigger
Create Date: 2026-09-15
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0019_params"
down_revision: str | Sequence[str] | None = "0018_drop_normative_trigger"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CALCULATE_NORMATIVE = """
CREATE OR REPLACE FUNCTION calculate_normative(
    p_product_code INTEGER,
    p_warehouse_code INTEGER
) RETURNS DECIMAL(12,2) AS $$
DECLARE
    v_monthly_consumption DECIMAL(12,2);
    v_category CHAR(1);
    v_long_distance BOOLEAN;
    v_category_factor DECIMAL(3,1);
    v_distance_factor DECIMAL(3,1);
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

    SELECT
        CASE v_category
            WHEN 'A' THEN category_a
            WHEN 'B' THEN category_b
            WHEN 'C' THEN category_c
            ELSE 1
        END,
        CASE WHEN v_long_distance THEN remote_warehouse ELSE 1 END
    INTO v_category_factor, v_distance_factor
    FROM params
    WHERE id = 1;

    v_result := v_monthly_consumption
        * COALESCE(v_distance_factor, 1)
        * COALESCE(v_category_factor, 1);

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
            WHEN 'A' THEN COALESCE(prm.category_a, 1)
            WHEN 'B' THEN COALESCE(prm.category_b, 1.5)
            WHEN 'C' THEN COALESCE(prm.category_c, 2)
            ELSE 1
          END
        * CASE WHEN o.long_distance THEN COALESCE(prm.remote_warehouse, 1.5) ELSE 1 END
        AS requirement,
    n.unit AS normative_unit,
    COALESCE(ab.available, 0) AS available,
    COALESCE(ab.plan, 0) AS plan,
    COALESCE(ab.unit, 'шт') AS fact_unit,
    (
        n.quantity
        * CASE p.category
            WHEN 'A' THEN COALESCE(prm.category_a, 1)
            WHEN 'B' THEN COALESCE(prm.category_b, 1.5)
            WHEN 'C' THEN COALESCE(prm.category_c, 2)
            ELSE 1
          END
        * CASE WHEN o.long_distance THEN COALESCE(prm.remote_warehouse, 1.5) ELSE 1 END
        - COALESCE(ab.plan, 0)
    ) AS deficit,
    n.expiry_date,
    n.client_name,
    CASE
        WHEN (
            n.quantity
            * CASE p.category
                WHEN 'A' THEN COALESCE(prm.category_a, 1)
                WHEN 'B' THEN COALESCE(prm.category_b, 1.5)
                WHEN 'C' THEN COALESCE(prm.category_c, 2)
                ELSE 1
              END
            * CASE
                WHEN o.long_distance THEN COALESCE(prm.remote_warehouse, 1.5)
                ELSE 1
              END
            - COALESCE(ab.plan, 0)
        ) > 0 THEN 'warning'
        ELSE 'ok'
    END AS status
FROM normatives n
JOIN objects o ON n.warehouse_code = o.code
JOIN products p ON n.product_code = p.code
LEFT JOIN params prm ON prm.id = 1
LEFT JOIN available_balances ab
    ON n.warehouse_code = ab.warehouse_code
    AND n.product_code = ab.product_code
WHERE n.deleted_at IS NULL
  AND n.expiry_date >= CURRENT_DATE
  AND (
        n.quantity
        * CASE p.category
            WHEN 'A' THEN COALESCE(prm.category_a, 1)
            WHEN 'B' THEN COALESCE(prm.category_b, 1.5)
            WHEN 'C' THEN COALESCE(prm.category_c, 2)
            ELSE 1
          END
        * CASE WHEN o.long_distance THEN COALESCE(prm.remote_warehouse, 1.5) ELSE 1 END
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


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS params (
            id INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),
            category_a DECIMAL(3,1) NOT NULL DEFAULT 1.0
                CHECK (category_a >= 1 AND category_a <= 3),
            category_b DECIMAL(3,1) NOT NULL DEFAULT 1.5
                CHECK (category_b >= 1 AND category_b <= 3),
            category_c DECIMAL(3,1) NOT NULL DEFAULT 2.0
                CHECK (category_c >= 1 AND category_c <= 3),
            remote_warehouse DECIMAL(3,1) NOT NULL DEFAULT 1.5
                CHECK (remote_warehouse >= 1 AND remote_warehouse <= 3),
            pallet_multiple BOOLEAN NOT NULL DEFAULT false,
            last_modified_by UUID REFERENCES users(id) ON DELETE SET NULL,
            last_modified_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_params_last_modified_by
            ON params(last_modified_by);
        """)
    op.execute("""
        INSERT INTO params (id)
        VALUES (1)
        ON CONFLICT (id) DO NOTHING;
        """)
    op.execute("DROP VIEW IF EXISTS deficit_view;")
    op.execute(DEFICIT_VIEW)
    op.execute(CALCULATE_NORMATIVE)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS deficit_view;")
    op.execute(DEFICIT_VIEW_OLD)
    op.execute(CALCULATE_NORMATIVE_OLD)
    op.execute("DROP INDEX IF EXISTS idx_params_last_modified_by;")
    op.execute("DROP TABLE IF EXISTS params;")
