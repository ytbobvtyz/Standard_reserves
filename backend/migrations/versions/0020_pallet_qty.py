"""Add optional pallet quantity on products.

Revision ID: 0020_pallet_qty
Revises: 0019_params
Create Date: 2026-09-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0020_pallet_qty"
down_revision: str | Sequence[str] | None = "0019_params"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column("pallet_qty", sa.Integer(), nullable=True),
    )
    op.create_check_constraint(
        "ck_products_pallet_qty",
        "products",
        "pallet_qty IS NULL OR pallet_qty >= 1",
    )


def downgrade() -> None:
    op.drop_constraint("ck_products_pallet_qty", "products", type_="check")
    op.drop_column("products", "pallet_qty")
