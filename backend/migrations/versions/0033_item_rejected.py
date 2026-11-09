"""Line rejection on a request item.

Revision ID: 0033_item_rejected
Revises: 0032_coverage_months
Create Date: 2026-11-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0033_item_rejected"
down_revision: str | Sequence[str] | None = "0032_coverage_months"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "request_items",
        sa.Column(
            "rejected",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.execute(
        "ALTER TABLE request_item_history "
        "DROP CONSTRAINT IF EXISTS ck_request_item_history_field_name"
    )
    op.execute(
        "ALTER TABLE request_item_history "
        "DROP CONSTRAINT IF EXISTS request_item_history_field_name_check"
    )
    op.create_check_constraint(
        "ck_request_item_history_field_name",
        "request_item_history",
        "field_name IN ('quantity_requested', 'quantity_approved', 'rejected')",
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE request_item_history "
        "DROP CONSTRAINT IF EXISTS ck_request_item_history_field_name"
    )
    op.create_check_constraint(
        "request_item_history_field_name_check",
        "request_item_history",
        "field_name IN ('quantity_requested', 'quantity_approved')",
    )
    op.drop_column("request_items", "rejected")
