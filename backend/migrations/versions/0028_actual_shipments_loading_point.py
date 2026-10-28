"""Shipping point on actual shipments.

Revision ID: 0028_shipment_point
Revises: 0027_actual_shipments
Create Date: 2026-10-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0028_shipment_point"
down_revision: str | Sequence[str] | None = "0027_actual_shipments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "actual_shipments",
        sa.Column("loading_point", sa.String(length=10), nullable=True),
    )
    op.execute(
        "UPDATE actual_shipments SET loading_point = 'н/д' WHERE loading_point IS NULL"
    )
    op.alter_column("actual_shipments", "loading_point", nullable=False)
    op.create_index(
        "idx_actual_shipments_loading_point",
        "actual_shipments",
        ["loading_point"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_actual_shipments_loading_point",
        table_name="actual_shipments",
    )
    op.drop_column("actual_shipments", "loading_point")
