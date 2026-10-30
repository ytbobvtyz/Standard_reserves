"""Extended stock fields on available balances.

Revision ID: 0029_balance_extended
Revises: 0028_shipment_point
Create Date: 2026-10-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0029_balance_extended"
down_revision: str | Sequence[str] | None = "0028_shipment_point"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_UNIT_KG = "unit IN ('шт', 'т', 'ШТ', 'КГ', 'кг')"
_UNIT_LEGACY = "unit IN ('шт', 'т', 'ШТ', 'КГ')"


def _add_amount(table: str, name: str) -> None:
    op.add_column(
        table,
        sa.Column(
            name,
            sa.Numeric(12, 2),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )


def upgrade() -> None:
    for name in ("full_stock", "on_way", "no_ready", "ready", "collected"):
        _add_amount("available_balances", name)
    _add_amount("available_balances_history", "full_stock")
    op.execute(
        "ALTER TABLE available_balances "
        "DROP CONSTRAINT IF EXISTS available_balances_unit_check"
    )
    op.execute(
        "ALTER TABLE available_balances "
        "DROP CONSTRAINT IF EXISTS ck_available_balances_unit"
    )
    op.execute(
        "ALTER TABLE available_balances "
        f"ADD CONSTRAINT ck_available_balances_unit CHECK ({_UNIT_KG})"
    )


def downgrade() -> None:
    op.execute("UPDATE available_balances SET unit = 'КГ' WHERE unit = 'кг'")
    op.execute(
        "ALTER TABLE available_balances "
        "DROP CONSTRAINT IF EXISTS ck_available_balances_unit"
    )
    op.execute(
        "ALTER TABLE available_balances "
        f"ADD CONSTRAINT ck_available_balances_unit CHECK ({_UNIT_LEGACY})"
    )
    op.drop_column("available_balances_history", "full_stock")
    for name in ("collected", "ready", "no_ready", "on_way", "full_stock"):
        op.drop_column("available_balances", name)
