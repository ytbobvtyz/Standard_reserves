"""Allow ШТ and КГ in available_balances.unit.

Revision ID: 0009_balance_unit_kg
Revises: 0008_balances_available_plan
Create Date: 2026-08-21
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0009_balance_unit_kg"
down_revision: str | Sequence[str] | None = "0008_balances_available_plan"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE available_balances "
        "DROP CONSTRAINT IF EXISTS available_balances_unit_check;"
    )
    op.execute(
        "ALTER TABLE available_balances "
        "DROP CONSTRAINT IF EXISTS ck_available_balances_unit;"
    )
    op.execute("""
        ALTER TABLE available_balances
            ADD CONSTRAINT ck_available_balances_unit
            CHECK (unit IN ('шт', 'т', 'ШТ', 'КГ'));
        """)


def downgrade() -> None:
    op.execute(
        "ALTER TABLE available_balances "
        "DROP CONSTRAINT IF EXISTS ck_available_balances_unit;"
    )
    op.execute("""
        ALTER TABLE available_balances
            ADD CONSTRAINT available_balances_unit_check
            CHECK (unit IN ('шт', 'т'));
        """)
