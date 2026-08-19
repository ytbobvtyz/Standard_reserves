"""Create SQL functions, views, and triggers.

Revision ID: 0003_functions_views_triggers
Revises: 0002_create_indexes
Create Date: 2026-08-18
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003_functions_views_triggers"
down_revision: str | Sequence[str] | None = "0002_create_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        CREATE OR REPLACE FUNCTION convert_to_tons(
            p_product_code INTEGER,
            p_quantity_units DECIMAL(12,2)
        ) RETURNS DECIMAL(12,2) AS $$
        DECLARE
            v_weight DECIMAL(12,4);
        BEGIN
            SELECT weight_kg INTO v_weight
            FROM products
            WHERE code = p_product_code;

            RETURN (p_quantity_units * v_weight) / 1000;
        END;
        $$ LANGUAGE plpgsql;
        """)
    op.execute("""
        CREATE OR REPLACE FUNCTION convert_to_units(
            p_product_code INTEGER,
            p_quantity_tons DECIMAL(12,2)
        ) RETURNS DECIMAL(12,2) AS $$
        DECLARE
            v_weight DECIMAL(12,4);
        BEGIN
            SELECT weight_kg INTO v_weight
            FROM products
            WHERE code = p_product_code;

            RETURN (p_quantity_tons * 1000) / v_weight;
        END;
        $$ LANGUAGE plpgsql;
        """)
    op.execute("""
        CREATE OR REPLACE FUNCTION get_related_products(
            p_product_code INTEGER
        ) RETURNS TABLE(product_code INTEGER) AS $$
        BEGIN
            RETURN QUERY
            WITH RECURSIVE
            ancestors AS (
                SELECT code, parent_code, children_code
                FROM products
                WHERE code = p_product_code
                  AND deleted_at IS NULL

                UNION

                SELECT p.code, p.parent_code, p.children_code
                FROM products p
                JOIN ancestors a ON p.code = a.parent_code
                WHERE p.deleted_at IS NULL
            ),
            descendants AS (
                SELECT code, parent_code, children_code
                FROM products
                WHERE code = p_product_code
                  AND deleted_at IS NULL

                UNION

                SELECT p.code, p.parent_code, p.children_code
                FROM products p
                JOIN descendants d ON p.code = d.children_code
                WHERE p.deleted_at IS NULL
            )
            SELECT DISTINCT q.code
            FROM (
                SELECT ancestors.code FROM ancestors
                UNION
                SELECT descendants.code FROM descendants
            ) q
            WHERE q.code != p_product_code;
        END;
        $$ LANGUAGE plpgsql;
        """)
    op.execute("""
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
        """)
    op.execute("""
        CREATE OR REPLACE FUNCTION expire_normatives()
        RETURNS void AS $$
        BEGIN
            UPDATE requests
            SET status = 'expired'
            WHERE status = 'active'
              AND expiry_date < CURRENT_DATE;

            UPDATE normatives
            SET deleted_at = NOW()
            WHERE deleted_at IS NULL
              AND expiry_date < CURRENT_DATE;

            INSERT INTO events (event_type, request_id, payload)
            SELECT 'normative_expired', id, jsonb_build_object(
                'expiry_date', expiry_date,
                'client_name', client_name
            )
            FROM requests
            WHERE status = 'expired'
              AND NOT EXISTS (
                  SELECT 1 FROM events
                  WHERE events.request_id = requests.id
                    AND events.event_type = 'normative_expired'
                    AND events.created_at > CURRENT_DATE - INTERVAL '1 day'
              );
        END;
        $$ LANGUAGE plpgsql;
        """)
    op.execute("""
        CREATE OR REPLACE VIEW deficit_view AS
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
        """)
    op.execute("""
        CREATE OR REPLACE VIEW normatives_on_date AS
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
        """)
    op.execute("""
        CREATE OR REPLACE FUNCTION trigger_request_created_event()
        RETURNS TRIGGER AS $$
        BEGIN
            INSERT INTO events (event_type, request_id, payload)
            VALUES (
                'request_created',
                NEW.id,
                jsonb_build_object(
                    'request_type', NEW.request_type,
                    'client_name', NEW.client_name,
                    'initiator_id', NEW.initiator_id
                )
            );
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """)
    op.execute("""
        CREATE TRIGGER request_created_event
        AFTER INSERT ON requests
        FOR EACH ROW
        EXECUTE FUNCTION trigger_request_created_event();
        """)
    op.execute("""
        CREATE OR REPLACE FUNCTION trigger_create_normative()
        RETURNS TRIGGER AS $$
        DECLARE
            item RECORD;
            v_category CHAR(1);
        BEGIN
            IF NEW.request_type != 'normative' THEN
                RETURN NEW;
            END IF;

            IF NEW.status = 'active' AND OLD.status = 'economy_check' THEN
                FOR item IN
                    SELECT
                        ri.product_code,
                        ri.warehouse_code,
                        COALESCE(ri.quantity_approved, ri.quantity_requested)
                            AS quantity,
                        ri.unit,
                        NEW.client_name,
                        NEW.expiry_date
                    FROM request_items ri
                    WHERE ri.request_id = NEW.id
                LOOP
                    SELECT category INTO v_category
                    FROM products
                    WHERE code = item.product_code;

                    INSERT INTO normatives (
                        request_id,
                        product_code,
                        warehouse_code,
                        quantity,
                        unit,
                        client_name,
                        expiry_date,
                        category
                    ) VALUES (
                        NEW.id,
                        item.product_code,
                        item.warehouse_code,
                        item.quantity,
                        item.unit,
                        item.client_name,
                        item.expiry_date,
                        v_category
                    );
                END LOOP;

                INSERT INTO events (event_type, request_id, payload)
                VALUES (
                    'normative_active',
                    NEW.id,
                    jsonb_build_object(
                        'expiry_date', NEW.expiry_date,
                        'client_name', NEW.client_name
                    )
                );
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """)
    op.execute("""
        CREATE TRIGGER create_normative_on_approve
        AFTER UPDATE OF status ON requests
        FOR EACH ROW
        WHEN (NEW.status = 'active' AND OLD.status = 'economy_check')
        EXECUTE FUNCTION trigger_create_normative();
        """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS create_normative_on_approve ON requests;")
    op.execute("DROP TRIGGER IF EXISTS request_created_event ON requests;")
    op.execute("DROP FUNCTION IF EXISTS trigger_create_normative();")
    op.execute("DROP FUNCTION IF EXISTS trigger_request_created_event();")
    op.execute("DROP VIEW IF EXISTS normatives_on_date;")
    op.execute("DROP VIEW IF EXISTS deficit_view;")
    op.execute("DROP FUNCTION IF EXISTS expire_normatives();")
    op.execute("DROP FUNCTION IF EXISTS calculate_normative(INTEGER, INTEGER);")
    op.execute("DROP FUNCTION IF EXISTS get_related_products(INTEGER);")
    op.execute("DROP FUNCTION IF EXISTS convert_to_units(INTEGER, NUMERIC);")
    op.execute("DROP FUNCTION IF EXISTS convert_to_tons(INTEGER, NUMERIC);")
