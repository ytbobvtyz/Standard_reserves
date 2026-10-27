"""Actual client shipments loaded from Excel.

Revision ID: 0027_actual_shipments
Revises: 0026_available_balances_history
Create Date: 2026-10-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision: str = "0027_actual_shipments"
down_revision: str | Sequence[str] | None = "0026_available_balances_history"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "actual_shipments",
        sa.Column(
            "id",
            PG_UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "client_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("clients.id"),
            nullable=False,
        ),
        sa.Column(
            "product_code",
            sa.Integer(),
            sa.ForeignKey("products.code"),
            nullable=False,
        ),
        sa.Column("quantity", sa.Numeric(12, 2), nullable=False),
        sa.Column("unit", sa.String(length=10), nullable=False),
        sa.Column("shipment_date", sa.Date(), nullable=False),
        sa.Column("invoice_number", sa.String(length=25), nullable=True),
        sa.Column("route", sa.String(length=50), nullable=True),
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
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "unit IN ('шт', 'кг', 'т')",
            name="ck_actual_shipments_unit",
        ),
        sa.CheckConstraint(
            "quantity > 0",
            name="ck_actual_shipments_quantity",
        ),
    )
    op.create_index("idx_actual_shipments_client", "actual_shipments", ["client_id"])
    op.create_index(
        "idx_actual_shipments_product",
        "actual_shipments",
        ["product_code"],
    )
    op.create_index("idx_actual_shipments_date", "actual_shipments", ["shipment_date"])
    op.create_index(
        "idx_actual_shipments_client_date",
        "actual_shipments",
        ["client_id", "shipment_date"],
    )


def downgrade() -> None:
    op.drop_table("actual_shipments")
