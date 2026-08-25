"""Add departments catalog and department_id on users and requests.

Revision ID: 0016_departments
Revises: 0015_object_long_distance, 0012_drop_unused_statuses
Create Date: 2026-08-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision: str = "0016_departments"
down_revision: str | Sequence[str] | None = (
    "0015_object_long_distance",
    "0012_drop_unused_statuses",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "departments",
        sa.Column(
            "id",
            PG_UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
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
    )
    op.create_index(
        "uq_departments_name",
        "departments",
        ["name"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "idx_departments_is_active",
        "departments",
        ["is_active"],
        postgresql_where=sa.text("is_active = true"),
    )

    op.add_column(
        "users",
        sa.Column("department_id", PG_UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_users_department_id",
        "users",
        "departments",
        ["department_id"],
        ["id"],
    )
    op.create_index("idx_users_department_id", "users", ["department_id"])

    op.add_column(
        "requests",
        sa.Column("department_id", PG_UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_requests_department_id",
        "requests",
        "departments",
        ["department_id"],
        ["id"],
    )
    op.create_index("idx_requests_department_id", "requests", ["department_id"])

    op.execute("""
        INSERT INTO departments (name, is_active)
        SELECT DISTINCT u.department, true
        FROM users u
        WHERE u.department IS NOT NULL
          AND btrim(u.department) <> ''
          AND u.deleted_at IS NULL
          AND NOT EXISTS (
              SELECT 1 FROM departments d
              WHERE d.name = u.department
                AND d.deleted_at IS NULL
          )
        """)
    op.execute("""
        UPDATE users u
        SET department_id = d.id
        FROM departments d
        WHERE u.department_id IS NULL
          AND u.department IS NOT NULL
          AND d.name = u.department
          AND d.deleted_at IS NULL
        """)
    op.execute("""
        UPDATE requests r
        SET department_id = u.department_id
        FROM users u
        WHERE r.department_id IS NULL
          AND r.initiator_id = u.id
          AND u.department_id IS NOT NULL
        """)


def downgrade() -> None:
    op.drop_index("idx_requests_department_id", table_name="requests")
    op.drop_constraint("fk_requests_department_id", "requests", type_="foreignkey")
    op.drop_column("requests", "department_id")
    op.drop_index("idx_users_department_id", table_name="users")
    op.drop_constraint("fk_users_department_id", "users", type_="foreignkey")
    op.drop_column("users", "department_id")
    op.drop_index("idx_departments_is_active", table_name="departments")
    op.drop_index("uq_departments_name", table_name="departments")
    op.drop_table("departments")
