"""Log changes of an active normative expiry date.

Revision ID: 0035_request_expiry_changed
Revises: 0034_admin_role_and_activity
Create Date: 2026-11-10
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0035_request_expiry_changed"
down_revision: str | Sequence[str] | None = "0034_admin_role_and_activity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EVENT_TYPES = (
    "'request_created', 'request_submitted', 'request_approved', "
    "'request_rejected', 'request_deleted', 'request_expiry_changed', "
    "'normative_active', 'normative_expired', 'deficit_detected', "
    "'deficit_resolved', 'normative_replaced_by_name', "
    "'user_registered', 'user_updated', 'user_deleted', 'password_changed', "
    "'product_created', 'product_updated', 'product_deleted', "
    "'client_created', 'client_updated', 'client_deleted', "
    "'object_created', 'object_updated', 'object_deleted', "
    "'balances_uploaded', 'actual_shipments_uploaded', "
    "'production_request_uploaded', 'export_generated'"
)

EVENT_TYPES_OLD = (
    "'request_created', 'request_submitted', 'request_approved', "
    "'request_rejected', 'request_deleted', "
    "'normative_active', 'normative_expired', 'deficit_detected', "
    "'deficit_resolved', 'normative_replaced_by_name', "
    "'user_registered', 'user_updated', 'user_deleted', 'password_changed', "
    "'product_created', 'product_updated', 'product_deleted', "
    "'client_created', 'client_updated', 'client_deleted', "
    "'object_created', 'object_updated', 'object_deleted', "
    "'balances_uploaded', 'actual_shipments_uploaded', "
    "'production_request_uploaded', 'export_generated'"
)


def _set_event_types(types_sql: str) -> None:
    op.execute("""
        DO $$
        DECLARE
            constraint_name text;
        BEGIN
            FOR constraint_name IN
                SELECT con.conname
                FROM pg_constraint con
                JOIN pg_class rel ON rel.oid = con.conrelid
                WHERE rel.relname = 'events'
                  AND con.contype = 'c'
                  AND pg_get_constraintdef(con.oid) ILIKE '%event_type%'
            LOOP
                EXECUTE format(
                    'ALTER TABLE events DROP CONSTRAINT %I',
                    constraint_name
                );
            END LOOP;
        END $$;
        """)
    op.execute(
        "ALTER TABLE events ADD CONSTRAINT ck_events_event_type "
        f"CHECK (event_type IN ({types_sql}))"
    )


def upgrade() -> None:
    _set_event_types(EVENT_TYPES)


def downgrade() -> None:
    op.execute("DELETE FROM events WHERE event_type = 'request_expiry_changed'")
    _set_event_types(EVENT_TYPES_OLD)
