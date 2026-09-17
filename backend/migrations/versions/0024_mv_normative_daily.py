"""Create materialized view mv_normative_daily for dashboard charts.

Revision ID: 0024_mv_normative_daily
Revises: 0023_prod_qty_scale
Create Date: 2026-09-16
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0024_mv_normative_daily"
down_revision: str | Sequence[str] | None = "0023_prod_qty_scale"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MV_NORMATIVE_DAILY = """
CREATE MATERIALIZED VIEW mv_normative_daily AS
SELECT
    n.created_at::date AS snapshot_date,
    n.warehouse_code,
    o.name AS warehouse_name,
    n.product_code,
    p.name AS product_name,
    p.category,
    SUM(n.quantity) AS total_normative,
    COUNT(DISTINCT n.id) AS count_active
FROM normatives n
JOIN objects o ON n.warehouse_code = o.code
JOIN products p ON n.product_code = p.code
WHERE n.deleted_at IS NULL
  AND n.expiry_date >= CURRENT_DATE
GROUP BY
    n.created_at::date,
    n.warehouse_code,
    o.name,
    n.product_code,
    p.name,
    p.category;
"""


def upgrade() -> None:
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_normative_daily")
    op.execute(MV_NORMATIVE_DAILY)
    op.execute("""
        CREATE INDEX idx_mv_normative_daily
            ON mv_normative_daily(snapshot_date, warehouse_code, product_code)
        """)
    op.execute("""
        CREATE OR REPLACE FUNCTION refresh_mv_normative_daily_job()
        RETURNS void AS $$
        BEGIN
            REFRESH MATERIALIZED VIEW mv_normative_daily;
        END;
        $$ LANGUAGE plpgsql;
        """)
    op.execute("""
        CREATE OR REPLACE FUNCTION trigger_refresh_mv_normative_daily()
        RETURNS trigger AS $$
        BEGIN
            REFRESH MATERIALIZED VIEW mv_normative_daily;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
        """)
    op.execute("""
        DROP TRIGGER IF EXISTS trg_refresh_mv_normative_daily_on_balances
            ON available_balances
        """)
    op.execute("""
        CREATE TRIGGER trg_refresh_mv_normative_daily_on_balances
        AFTER INSERT OR UPDATE OR DELETE ON available_balances
        FOR EACH STATEMENT
        EXECUTE FUNCTION trigger_refresh_mv_normative_daily()
        """)


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_refresh_mv_normative_daily_on_balances "
        "ON available_balances"
    )
    op.execute("DROP FUNCTION IF EXISTS trigger_refresh_mv_normative_daily()")
    op.execute("DROP FUNCTION IF EXISTS refresh_mv_normative_daily_job()")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_normative_daily")
