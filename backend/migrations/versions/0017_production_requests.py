"""Add production request batches for normative Excel uploads.

Revision ID: 0017_production_requests
Revises: 0016_departments
Create Date: 2026-08-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision: str = "0017_production_requests"
down_revision: str | Sequence[str] | None = "0016_departments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "production_requests",
        sa.Column(
            "id",
            PG_UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "batch_id",
            PG_UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "source",
            sa.String(length=50),
            nullable=False,
            server_default=sa.text("'excel_upload'"),
        ),
        sa.Column(
            "uploaded_by",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("client_name", sa.Text(), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "source IN ('excel_upload')",
            name="ck_production_requests_source",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'archived', 'cancelled')",
            name="ck_production_requests_status",
        ),
        sa.CheckConstraint(
            "valid_to >= valid_from",
            name="ck_production_requests_dates",
        ),
    )
    op.create_index(
        "uq_production_requests_batch_id",
        "production_requests",
        ["batch_id"],
        unique=True,
    )
    op.create_index(
        "idx_production_requests_uploaded_by",
        "production_requests",
        ["uploaded_by"],
    )
    op.create_index(
        "idx_production_requests_status",
        "production_requests",
        ["status"],
    )
    op.create_index(
        "idx_production_requests_deleted_at",
        "production_requests",
        ["deleted_at"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "production_request_items",
        sa.Column(
            "id",
            PG_UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "production_request_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("production_requests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "product_code",
            sa.Integer(),
            sa.ForeignKey("products.code"),
            nullable=False,
        ),
        sa.Column(
            "warehouse_code",
            sa.Integer(),
            sa.ForeignKey("objects.code"),
            nullable=False,
        ),
        sa.Column("quantity", sa.Numeric(12, 2), nullable=False),
        sa.Column("unit", sa.String(length=10), nullable=False),
        sa.Column("client_name", sa.Text(), nullable=False),
        sa.Column("category", sa.CHAR(length=1), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "unit IN ('шт', 'кг', 'т')",
            name="ck_production_request_items_unit",
        ),
        sa.CheckConstraint(
            "category IN ('A', 'B', 'C')",
            name="ck_production_request_items_category",
        ),
        sa.CheckConstraint(
            "quantity > 0",
            name="ck_production_request_items_quantity",
        ),
    )
    op.create_index(
        "idx_production_request_items_request",
        "production_request_items",
        ["production_request_id"],
    )
    op.create_index(
        "idx_production_request_items_product_warehouse",
        "production_request_items",
        ["product_code", "warehouse_code"],
    )

    op.alter_column("normatives", "request_id", nullable=True)
    op.add_column(
        "normatives",
        sa.Column(
            "production_request_item_id",
            PG_UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_normatives_production_request_item_id",
        "normatives",
        "production_request_items",
        ["production_request_item_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "uq_normatives_production_request_item_id",
        "normatives",
        ["production_request_item_id"],
        unique=True,
    )
    op.execute("ALTER TABLE normatives " "DROP CONSTRAINT IF EXISTS ck_normatives_unit")
    op.execute(
        "ALTER TABLE normatives " "DROP CONSTRAINT IF EXISTS normatives_unit_check"
    )
    op.create_check_constraint(
        "ck_normatives_unit",
        "normatives",
        "unit IN ('шт', 'кг', 'т')",
    )


def downgrade() -> None:
    op.execute("ALTER TABLE normatives " "DROP CONSTRAINT IF EXISTS ck_normatives_unit")
    op.create_check_constraint(
        "ck_normatives_unit",
        "normatives",
        "unit IN ('шт', 'т')",
    )
    op.drop_index(
        "uq_normatives_production_request_item_id",
        table_name="normatives",
    )
    op.drop_constraint(
        "fk_normatives_production_request_item_id",
        "normatives",
        type_="foreignkey",
    )
    op.drop_column("normatives", "production_request_item_id")
    op.execute("DELETE FROM normatives WHERE request_id IS NULL")
    op.alter_column("normatives", "request_id", nullable=False)

    op.drop_index(
        "idx_production_request_items_product_warehouse",
        table_name="production_request_items",
    )
    op.drop_index(
        "idx_production_request_items_request",
        table_name="production_request_items",
    )
    op.drop_table("production_request_items")

    op.drop_index(
        "idx_production_requests_deleted_at",
        table_name="production_requests",
    )
    op.drop_index(
        "idx_production_requests_status",
        table_name="production_requests",
    )
    op.drop_index(
        "idx_production_requests_uploaded_by",
        table_name="production_requests",
    )
    op.drop_index(
        "uq_production_requests_batch_id",
        table_name="production_requests",
    )
    op.drop_table("production_requests")
