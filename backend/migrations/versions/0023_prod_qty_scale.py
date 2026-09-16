"""Widen production and normative quantities for tons precision.

Revision ID: 0023_prod_qty_scale
Revises: 0022_request_qty_6dp
Create Date: 2026-09-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0023_prod_qty_scale"
down_revision: str | Sequence[str] | None = "0022_request_qty_6dp"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NORMATIVES_ON_DATE_VIEW = """
CREATE VIEW normatives_on_date AS
SELECT
    n.warehouse_code,
    o.name AS warehouse_name,
    n.product_code,
    p.name AS product_name,
    n.quantity,
    n.unit,
    n.client_name,
    n.expiry_date,
    n.category,
    n.created_at,
    (
        SELECT SUM(n2.quantity)
        FROM normatives n2
        WHERE n2.warehouse_code = n.warehouse_code
          AND n2.product_code = n.product_code
          AND n2.created_at::date <= CURRENT_DATE
          AND n2.expiry_date >= CURRENT_DATE
          AND n2.deleted_at IS NULL
    ) AS total_normative_on_date
FROM normatives n
JOIN objects o ON n.warehouse_code = o.code
JOIN products p ON n.product_code = p.code
WHERE n.deleted_at IS NULL;
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


def _drop_dependent_views() -> None:
    op.execute("DROP VIEW IF EXISTS deficit_view")
    op.execute("DROP VIEW IF EXISTS normatives_on_date")


def _restore_dependent_views() -> None:
    op.execute(NORMATIVES_ON_DATE_VIEW)
    op.execute(DEFICIT_VIEW)


def upgrade() -> None:
    qty = sa.Numeric(16, 6)
    _drop_dependent_views()
    op.alter_column(
        "production_request_items",
        "quantity",
        existing_type=sa.Numeric(12, 2),
        type_=qty,
        existing_nullable=False,
    )
    op.alter_column(
        "normatives",
        "quantity",
        existing_type=sa.Numeric(12, 2),
        type_=qty,
        existing_nullable=False,
    )
    _restore_dependent_views()


def downgrade() -> None:
    qty = sa.Numeric(12, 2)
    _drop_dependent_views()
    op.alter_column(
        "normatives",
        "quantity",
        existing_type=sa.Numeric(16, 6),
        type_=qty,
        existing_nullable=False,
    )
    op.alter_column(
        "production_request_items",
        "quantity",
        existing_type=sa.Numeric(16, 6),
        type_=qty,
        existing_nullable=False,
    )
    _restore_dependent_views()
