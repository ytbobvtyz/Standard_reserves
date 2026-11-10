"""Role admin and activity columns on events.

Revision ID: 0034_admin_role_and_activity
Revises: 0033_item_rejected
Create Date: 2026-11-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision: str = "0034_admin_role_and_activity"
down_revision: str | Sequence[str] | None = "0033_item_rejected"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EVENT_TYPES_OLD = (
    "'request_created', 'request_approved', 'request_rejected', "
    "'normative_active', 'normative_expired', "
    "'deficit_detected', 'deficit_resolved', "
    "'normative_replaced_by_name'"
)


def _drop_checks(table: str, column_hint: str) -> None:
    op.execute(f"""
        DO $$
        DECLARE
            constraint_name text;
        BEGIN
            FOR constraint_name IN
                SELECT con.conname
                FROM pg_constraint con
                JOIN pg_class rel ON rel.oid = con.conrelid
                WHERE rel.relname = '{table}'
                  AND con.contype = 'c'
                  AND pg_get_constraintdef(con.oid) ILIKE '%{column_hint}%'
            LOOP
                EXECUTE format(
                    'ALTER TABLE {table} DROP CONSTRAINT %I',
                    constraint_name
                );
            END LOOP;
        END $$;
        """)


def _set_event_types(types_sql: str) -> None:
    _drop_checks("events", "event_type")
    op.execute(
        "ALTER TABLE events ADD CONSTRAINT ck_events_event_type "
        f"CHECK (event_type IN ({types_sql}))"
    )


def _set_roles(roles_sql: str) -> None:
    _drop_checks("users", "role")
    op.execute(
        "ALTER TABLE users ADD CONSTRAINT ck_users_role "
        f"CHECK (role IN ({roles_sql}))"
    )


def upgrade() -> None:
    from app.bootstrap import ADMIN_USER, SEED_PASSWORD
    from app.core.security import hash_password
    from app.models.event import EVENT_TYPES
    from app.models.user import USER_ROLES

    roles_sql = ", ".join(f"'{role}'" for role in USER_ROLES)
    event_sql = ", ".join(f"'{item}'" for item in EVENT_TYPES)
    _set_roles(roles_sql)

    bind = op.get_bind()
    existing = bind.execute(
        sa.text("SELECT 1 FROM users WHERE username = :username OR id = :id LIMIT 1"),
        {"username": ADMIN_USER["username"], "id": ADMIN_USER["id"]},
    ).first()
    if existing is None:
        department_id = bind.execute(
            sa.text("SELECT id FROM departments WHERE id = :id"),
            {"id": ADMIN_USER["department_id"]},
        ).scalar()
        users = sa.table(
            "users",
            sa.column("id", PG_UUID(as_uuid=True)),
            sa.column("username", sa.String()),
            sa.column("email", sa.String()),
            sa.column("password_hash", sa.Text()),
            sa.column("full_name", sa.Text()),
            sa.column("role", sa.String()),
            sa.column("department", sa.Text()),
            sa.column("department_id", PG_UUID(as_uuid=True)),
            sa.column("is_active", sa.Boolean()),
        )
        bind.execute(
            users.insert().values(
                id=ADMIN_USER["id"],
                username=ADMIN_USER["username"],
                email=ADMIN_USER["email"],
                password_hash=hash_password(SEED_PASSWORD),
                full_name=ADMIN_USER["full_name"],
                role=ADMIN_USER["role"],
                department=ADMIN_USER["department"],
                department_id=department_id,
                is_active=True,
            )
        )

    op.add_column(
        "events",
        sa.Column("user_id", PG_UUID(as_uuid=True), nullable=True),
    )
    op.add_column("events", sa.Column("entity_type", sa.String(50), nullable=True))
    op.add_column(
        "events",
        sa.Column("entity_id", PG_UUID(as_uuid=True), nullable=True),
    )
    op.add_column("events", sa.Column("details", JSONB, nullable=True))
    op.create_foreign_key(
        "fk_events_user_id",
        "events",
        "users",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("idx_events_user_id", "events", ["user_id"])
    op.create_index("idx_events_entity", "events", ["entity_type", "entity_id"])
    _set_event_types(event_sql)


def downgrade() -> None:
    from app.bootstrap import ADMIN_USER

    op.drop_index("idx_events_entity", table_name="events")
    op.drop_index("idx_events_user_id", table_name="events")
    bind = op.get_bind()
    bind.execute(
        sa.text("DELETE FROM events WHERE user_id = :id"),
        {"id": ADMIN_USER["id"]},
    )
    op.drop_constraint("fk_events_user_id", "events", type_="foreignkey")
    op.drop_column("events", "details")
    op.drop_column("events", "entity_id")
    op.drop_column("events", "entity_type")
    op.drop_column("events", "user_id")

    new_types = (
        "'user_registered', 'user_updated', 'user_deleted', 'password_changed', "
        "'product_created', 'product_updated', 'product_deleted', "
        "'client_created', 'client_updated', 'client_deleted', "
        "'object_created', 'object_updated', 'object_deleted', "
        "'request_submitted', 'request_deleted', "
        "'balances_uploaded', 'actual_shipments_uploaded', "
        "'production_request_uploaded', 'export_generated'"
    )
    op.execute(f"DELETE FROM events WHERE event_type IN ({new_types})")
    _set_event_types(EVENT_TYPES_OLD)

    bind.execute(
        sa.text("DELETE FROM users WHERE id = :id OR role = 'admin'"),
        {"id": ADMIN_USER["id"]},
    )
    _set_roles("'commercial', 'pp', 'economist', 'logistics', 'guest'")
