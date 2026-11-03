"""Commercial normative start date.

Revision ID: 0031_normative_valid_from
Revises: 0030_auto_complete_previous
Create Date: 2026-11-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0031_normative_valid_from"
down_revision: str | Sequence[str] | None = "0030_auto_complete_previous"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("normatives", sa.Column("valid_from", sa.Date(), nullable=True))
    op.execute(
        "UPDATE normatives "
        "SET valid_from = (created_at AT TIME ZONE 'UTC')::date "
        "WHERE valid_from IS NULL"
    )
    op.alter_column(
        "normatives",
        "valid_from",
        existing_type=sa.Date(),
        nullable=False,
        server_default=sa.text("CURRENT_DATE"),
    )
    op.create_index("idx_normatives_valid_from", "normatives", ["valid_from"])


def downgrade() -> None:
    op.drop_index("idx_normatives_valid_from", table_name="normatives")
    op.drop_column("normatives", "valid_from")
