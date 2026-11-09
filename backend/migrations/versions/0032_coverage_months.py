"""Coverage thresholds on params.

Revision ID: 0032_coverage_months
Revises: 0031_normative_valid_from
Create Date: 2026-11-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0032_coverage_months"
down_revision: str | Sequence[str] | None = "0031_normative_valid_from"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "params",
        sa.Column(
            "coverage_high_months",
            sa.Numeric(4, 1),
            nullable=False,
            server_default="2.0",
        ),
    )
    op.add_column(
        "params",
        sa.Column(
            "coverage_low_months",
            sa.Numeric(4, 1),
            nullable=False,
            server_default="4.0",
        ),
    )
    op.create_check_constraint(
        "ck_params_coverage_high",
        "params",
        "coverage_high_months > 0 AND coverage_high_months <= 36",
    )
    op.create_check_constraint(
        "ck_params_coverage_low",
        "params",
        "coverage_low_months > coverage_high_months AND coverage_low_months <= 36",
    )


def downgrade() -> None:
    op.drop_constraint("ck_params_coverage_low", "params", type_="check")
    op.drop_constraint("ck_params_coverage_high", "params", type_="check")
    op.drop_column("params", "coverage_low_months")
    op.drop_column("params", "coverage_high_months")
