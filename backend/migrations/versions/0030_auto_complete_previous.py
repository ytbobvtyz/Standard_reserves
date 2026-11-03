"""Store the flag to close previous commercial normatives.

Revision ID: 0030_auto_complete_previous
Revises: 0029_balance_extended
Create Date: 2026-11-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0030_auto_complete_previous"
down_revision: str | Sequence[str] | None = "0029_balance_extended"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "requests",
        sa.Column(
            "auto_complete_previous",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("requests", "auto_complete_previous")
