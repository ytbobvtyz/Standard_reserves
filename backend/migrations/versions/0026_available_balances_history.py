"""Daily snapshots of available balances.

Revision ID: 0026_available_balances_history
Revises: 0025_clients
Create Date: 2026-10-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision: str = "0026_available_balances_history"
down_revision: str | Sequence[str] | None = "0025_clients"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "available_balances_history",
        sa.Column(
            "id",
            PG_UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("snapshot_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "warehouse_code",
            sa.Integer(),
            sa.ForeignKey("objects.code"),
            nullable=False,
        ),
        sa.Column(
            "product_code",
            sa.Integer(),
            sa.ForeignKey("products.code"),
            nullable=False,
        ),
        sa.Column("available", sa.Numeric(12, 2), nullable=False),
        sa.Column("plan", sa.Numeric(12, 2), nullable=False),
        sa.Column("unit", sa.String(length=10), nullable=False),
        sa.Column(
            "source",
            sa.String(length=50),
            nullable=False,
            server_default=sa.text("'excel_upload'"),
        ),
        sa.Column(
            "uploaded_by",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "unit IN ('шт', 'кг', 'т', 'ШТ', 'КГ')",
            name="ck_available_balances_history_unit",
        ),
    )
    op.create_index(
        "uq_available_history_daily",
        "available_balances_history",
        ["snapshot_date", "warehouse_code", "product_code"],
        unique=True,
    )
    op.create_index(
        "idx_available_history_date",
        "available_balances_history",
        ["snapshot_date"],
    )
    op.create_index(
        "idx_available_history_product",
        "available_balances_history",
        ["product_code", "snapshot_date"],
    )
    op.create_index(
        "idx_available_history_warehouse",
        "available_balances_history",
        ["warehouse_code", "snapshot_date"],
    )


def downgrade() -> None:
    op.drop_table("available_balances_history")
