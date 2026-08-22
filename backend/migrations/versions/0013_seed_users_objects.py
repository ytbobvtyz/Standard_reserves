"""Seed current users and objects. Other tables stay empty.

Revision ID: 0013_seed_users_objects
Revises: 0012_object_uniqueness
Create Date: 2026-08-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.dialects.postgresql import insert as pg_insert

revision: str = "0013_seed_users_objects"
down_revision: str | Sequence[str] | None = "0012_object_uniqueness"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    from app.bootstrap import OBJECTS, SEED_LOGISTICS_ID, SEED_PASSWORD, USERS
    from app.core.security import hash_password

    password_hash = hash_password(SEED_PASSWORD)
    bind = op.get_bind()

    users = sa.table(
        "users",
        sa.column("id", PG_UUID(as_uuid=True)),
        sa.column("username", sa.String()),
        sa.column("email", sa.String()),
        sa.column("password_hash", sa.Text()),
        sa.column("full_name", sa.Text()),
        sa.column("role", sa.String()),
        sa.column("department", sa.Text()),
        sa.column("is_active", sa.Boolean()),
    )
    objects = sa.table(
        "objects",
        sa.column("code", sa.Integer()),
        sa.column("name", sa.Text()),
        sa.column("city", sa.Text()),
        sa.column("region", sa.Text()),
        sa.column("type", sa.String()),
        sa.column("erp_plant_code", sa.Integer()),
        sa.column("erp_warehouse_code", sa.String()),
        sa.column("loading_point", sa.String()),
        sa.column("is_active", sa.Boolean()),
        sa.column("last_modified_by", PG_UUID(as_uuid=True)),
    )

    for item in USERS:
        bind.execute(
            pg_insert(users)
            .values(
                id=item["id"],
                username=item["username"],
                email=item["email"],
                password_hash=password_hash,
                full_name=item["full_name"],
                role=item["role"],
                department=item["department"],
                is_active=True,
            )
            .on_conflict_do_nothing(index_elements=["id"])
        )

    for item in OBJECTS:
        bind.execute(
            pg_insert(objects)
            .values(
                code=item["code"],
                name=item["name"],
                city=item["city"],
                region=item["region"],
                type=item["type"],
                erp_plant_code=item.get("erp_plant_code"),
                erp_warehouse_code=item.get("erp_warehouse_code"),
                loading_point=item.get("loading_point"),
                is_active=True,
                last_modified_by=SEED_LOGISTICS_ID,
            )
            .on_conflict_do_nothing(index_elements=["code"])
        )


def downgrade() -> None:
    from app.bootstrap import OBJECTS, USERS

    codes = ", ".join(str(item["code"]) for item in OBJECTS)
    user_ids = ", ".join(f"'{item['id']}'" for item in USERS)
    op.execute(f"DELETE FROM objects WHERE code IN ({codes})")
    op.execute(f"DELETE FROM users WHERE id IN ({user_ids})")
