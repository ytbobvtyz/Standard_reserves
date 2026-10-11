"""Add clients directory and client_id on requests and normatives.

Revision ID: 0025_clients
Revises: 0024_mv_normative_daily
Create Date: 2026-10-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision: str = "0025_clients"
down_revision: str | Sequence[str] | None = "0024_mv_normative_daily"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SYSTEM_CLIENT_ID = "00000000-0000-4000-8000-000000000001"

EVENT_TYPES_NEW = (
    "'request_created', 'request_approved', 'request_rejected', "
    "'normative_active', 'normative_expired', "
    "'deficit_detected', 'deficit_resolved', "
    "'normative_replaced_by_name'"
)
EVENT_TYPES_OLD = (
    "'request_created', 'request_approved', 'request_rejected', "
    "'normative_active', 'normative_expired', "
    "'deficit_detected', 'deficit_resolved'"
)

CLIENT_ID_TABLES = (
    "requests",
    "normatives",
    "production_requests",
    "production_request_items",
)


def _drop_event_type_checks() -> None:
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


def _set_event_types(types_sql: str) -> None:
    _drop_event_type_checks()
    op.execute(
        "ALTER TABLE events ADD CONSTRAINT ck_events_event_type "
        f"CHECK (event_type IN ({types_sql}))"
    )


def _backfill_by_name(table: str) -> None:
    op.execute(f"""
        UPDATE {table} AS row
        SET client_id = matched.client_id
        FROM (
            SELECT
                src.id AS row_id,
                CASE
                    WHEN src.client_name IS NULL OR btrim(src.client_name) = '' THEN
                        '{SYSTEM_CLIENT_ID}'::uuid
                    WHEN count(c.id) = 1 THEN
                        (array_agg(c.id))[1]
                    ELSE
                        '{SYSTEM_CLIENT_ID}'::uuid
                END AS client_id
            FROM {table} AS src
            LEFT JOIN clients AS c
                ON c.deleted_at IS NULL
               AND src.client_name IS NOT NULL
               AND btrim(src.client_name) <> ''
               AND lower(btrim(c.name)) = lower(btrim(src.client_name))
            GROUP BY src.id, src.client_name
        ) AS matched
        WHERE row.id = matched.row_id
        """)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.create_table(
        "clients",
        sa.Column(
            "id",
            PG_UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("client_code", sa.BigInteger(), nullable=False),
        sa.Column("inn", sa.String(12), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("kpp", sa.String(9), nullable=True),
        sa.Column("department_id", PG_UUID(as_uuid=True), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "is_system",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "client_code >= 1 AND client_code <= 9999999999",
            name="ck_clients_client_code",
        ),
        sa.ForeignKeyConstraint(
            ["department_id"],
            ["departments.id"],
            name="fk_clients_department_id",
            ondelete="RESTRICT",
        ),
    )
    op.create_index(
        "uq_clients_client_code",
        "clients",
        ["client_code"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "idx_clients_inn",
        "clients",
        ["inn"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index("idx_clients_department_id", "clients", ["department_id"])
    op.create_index(
        "idx_clients_is_active",
        "clients",
        ["is_active"],
        postgresql_where=sa.text("is_active = true"),
    )
    op.create_index(
        "idx_clients_name_trgm",
        "clients",
        ["name"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"name": "gin_trgm_ops"},
    )
    op.execute(f"""
        INSERT INTO clients (
            id, client_code, inn, name, is_system, is_active
        ) VALUES (
            '{SYSTEM_CLIENT_ID}',
            9999999999,
            '0000000000',
            'Общий клиент',
            true,
            true
        )
        """)

    for table in CLIENT_ID_TABLES:
        op.add_column(
            table,
            sa.Column("client_id", PG_UUID(as_uuid=True), nullable=True),
        )

    op.execute(
        "UPDATE requests SET client_id = "
        f"'{SYSTEM_CLIENT_ID}'::uuid "
        "WHERE client_id IS NULL"
    )
    op.execute(
        "UPDATE normatives SET client_id = "
        f"'{SYSTEM_CLIENT_ID}'::uuid "
        "WHERE client_id IS NULL"
    )
    _backfill_by_name("production_requests")
    _backfill_by_name("production_request_items")

    for table in CLIENT_ID_TABLES:
        op.alter_column(table, "client_id", nullable=False)
        op.create_foreign_key(
            f"fk_{table}_client_id",
            table,
            "clients",
            ["client_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        op.create_index(f"idx_{table}_client_id", table, ["client_id"])

    _set_event_types(EVENT_TYPES_NEW)


def downgrade() -> None:
    _set_event_types(EVENT_TYPES_OLD)
    for table in reversed(CLIENT_ID_TABLES):
        op.drop_index(f"idx_{table}_client_id", table_name=table)
        op.drop_constraint(f"fk_{table}_client_id", table, type_="foreignkey")
        op.drop_column(table, "client_id")
    op.drop_index("idx_clients_name_trgm", table_name="clients")
    op.drop_index("idx_clients_is_active", table_name="clients")
    op.drop_index("idx_clients_department_id", table_name="clients")
    op.drop_index("idx_clients_inn", table_name="clients")
    op.drop_index("uq_clients_client_code", table_name="clients")
    op.drop_table("clients")
