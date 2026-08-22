"""Remove pp_rework and economy_rework request statuses.

Revision ID: 0014_drop_rework_statuses
Revises: 0013_seed_users_objects
Create Date: 2026-08-22
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0014_drop_rework_statuses"
down_revision: str | Sequence[str] | None = "0013_seed_users_objects"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "UPDATE requests SET status = 'pp_approved' WHERE status = 'pp_rework';"
    )
    op.execute(
        "UPDATE requests SET status = 'economy_check' "
        "WHERE status = 'economy_rework';"
    )
    op.execute("ALTER TABLE requests DROP CONSTRAINT IF EXISTS ck_requests_status;")
    op.execute("ALTER TABLE requests DROP CONSTRAINT IF EXISTS requests_status_check;")
    op.execute(
        """
        ALTER TABLE requests
        ADD CONSTRAINT ck_requests_status CHECK (
            status IN (
                'draft',
                'pp_approved',
                'economy_check',
                'active',
                'approved',
                'rejected',
                'expired',
                'executed'
            )
        );
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE requests DROP CONSTRAINT IF EXISTS ck_requests_status;")
    op.execute("ALTER TABLE requests DROP CONSTRAINT IF EXISTS requests_status_check;")
    op.execute(
        """
        ALTER TABLE requests
        ADD CONSTRAINT ck_requests_status CHECK (
            status IN (
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
            )
        );
        """
    )
