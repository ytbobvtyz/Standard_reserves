"""Widen request item quantities so pallet rounding in tons keeps precision.

Revision ID: 0021_request_qty_scale
Revises: 0020_pallet_qty
Create Date: 2026-09-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0021_request_qty_scale"
down_revision: str | Sequence[str] | None = "0020_pallet_qty"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    qty = sa.Numeric(12, 5)
    op.alter_column(
        "request_items",
        "quantity_requested",
        existing_type=sa.Numeric(12, 2),
        type_=qty,
        existing_nullable=False,
    )
    op.alter_column(
        "request_items",
        "quantity_approved",
        existing_type=sa.Numeric(12, 2),
        type_=qty,
        existing_nullable=True,
    )
    op.alter_column(
        "request_item_history",
        "old_value",
        existing_type=sa.Numeric(12, 2),
        type_=qty,
        existing_nullable=True,
    )
    op.alter_column(
        "request_item_history",
        "new_value",
        existing_type=sa.Numeric(12, 2),
        type_=qty,
        existing_nullable=True,
    )


def downgrade() -> None:
    qty = sa.Numeric(12, 2)
    op.alter_column(
        "request_item_history",
        "new_value",
        existing_type=sa.Numeric(12, 5),
        type_=qty,
        existing_nullable=True,
    )
    op.alter_column(
        "request_item_history",
        "old_value",
        existing_type=sa.Numeric(12, 5),
        type_=qty,
        existing_nullable=True,
    )
    op.alter_column(
        "request_items",
        "quantity_approved",
        existing_type=sa.Numeric(12, 5),
        type_=qty,
        existing_nullable=True,
    )
    op.alter_column(
        "request_items",
        "quantity_requested",
        existing_type=sa.Numeric(12, 5),
        type_=qty,
        existing_nullable=False,
    )
