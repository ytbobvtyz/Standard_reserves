"""Drop create_normative_on_approve trigger from requests.

Revision ID: 0018_drop_normative_trigger
Revises: 0017_production_requests
Create Date: 2026-09-03
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0018_drop_normative_trigger"
down_revision: str | Sequence[str] | None = "0017_production_requests"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS create_normative_on_approve ON requests;")
    op.execute("DROP FUNCTION IF EXISTS trigger_create_normative();")


def downgrade() -> None:
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
