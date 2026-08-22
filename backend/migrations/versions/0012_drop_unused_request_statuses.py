"""Drop unused request statuses from CHECK constraint.

Revision ID: 0012_drop_unused_request_statuses
Revises: 0011_sync_metadata
Create Date: 2026-08-22
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0012_drop_unused_request_statuses"
down_revision: str | Sequence[str] | None = "0011_sync_metadata"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LIVE_STATUSES = (
    "draft",
    "pp_approved",
    "economy_check",
    "active",
    "approved",
    "rejected",
    "expired",
    "executed",
)


def upgrade() -> None:
    op.execute("ALTER TABLE requests DROP CONSTRAINT IF EXISTS requests_status_check")
    op.execute("ALTER TABLE requests DROP CONSTRAINT IF EXISTS ck_requests_status")
    statuses = ", ".join(f"'{item}'" for item in LIVE_STATUSES)
    op.execute(
        f"ALTER TABLE requests ADD CONSTRAINT ck_requests_status "
        f"CHECK (status IN ({statuses}))"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE requests DROP CONSTRAINT IF EXISTS ck_requests_status")
    op.execute(
        """
        ALTER TABLE requests ADD CONSTRAINT requests_status_check CHECK (status IN (
            'draft',
            'pp_approved',
            'economy_check',
            'pp_rework',
            'economy_rework',
            'active',
            'approved',
            'rejected',
            'expired',
            'executed'
        ))
        """
    )
