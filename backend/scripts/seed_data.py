"""Seed users and objects for a fresh or existing database.

Products, requests, balances and other tables are left empty.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.bootstrap import DEPARTMENTS, OBJECTS, SEED_LOGISTICS_ID, SEED_PASSWORD, USERS
from app.core.config import settings
from app.core.security import hash_password
from app.models import Department, Object, User


async def _upsert_department(session: AsyncSession, payload: dict) -> None:
    by_name = await session.scalar(
        select(Department).where(Department.name == payload["name"])
    )
    if by_name is not None:
        by_name.is_active = True
        by_name.deleted_at = None
        return
    existing = await session.get(Department, payload["id"])
    if existing is None:
        session.add(Department(**payload, is_active=True))
        return
    existing.name = payload["name"]
    existing.is_active = True
    existing.deleted_at = None


async def _upsert_user(session: AsyncSession, payload: dict) -> None:
    password_hash = hash_password(SEED_PASSWORD)
    department_id = payload.get("department_id")
    if payload.get("department"):
        department = await session.scalar(
            select(Department).where(Department.name == payload["department"])
        )
        if department is not None:
            department_id = department.id
    existing = await session.get(User, payload["id"])
    if existing is None:
        session.add(
            User(
                **{**payload, "department_id": department_id},
                password_hash=password_hash,
                is_active=True,
            )
        )
        return
    existing.password_hash = password_hash
    existing.username = payload["username"]
    existing.email = payload["email"]
    existing.full_name = payload["full_name"]
    existing.role = payload["role"]
    existing.department = payload["department"]
    existing.department_id = department_id
    existing.is_active = True
    existing.deleted_at = None


async def _upsert_object(session: AsyncSession, payload: dict) -> None:
    now = datetime.now(UTC)
    existing = await session.get(Object, payload["code"])
    if existing is None:
        session.add(
            Object(
                **payload,
                is_active=True,
                last_modified_by=SEED_LOGISTICS_ID,
                last_modified_at=now,
            )
        )
        return
    existing.name = payload["name"]
    existing.city = payload["city"]
    existing.region = payload["region"]
    existing.type = payload["type"]
    existing.erp_plant_code = payload.get("erp_plant_code")
    existing.erp_warehouse_code = payload.get("erp_warehouse_code")
    existing.loading_point = payload.get("loading_point")
    existing.is_active = True
    existing.deleted_at = None
    existing.last_modified_by = SEED_LOGISTICS_ID
    existing.last_modified_at = now


async def seed() -> None:
    engine = create_async_engine(settings.async_database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        for item in DEPARTMENTS:
            await _upsert_department(session, item)
        await session.flush()

        for item in USERS:
            await _upsert_user(session, item)
        await session.flush()

        for item in OBJECTS:
            await _upsert_object(session, item)

        await session.commit()

        users_count = len((await session.scalars(select(User))).all())
        objects_count = len(
            (
                await session.scalars(select(Object).where(Object.deleted_at.is_(None)))
            ).all()
        )
        plants = sum(1 for item in OBJECTS if item["type"] == "plant")
        warehouses = sum(1 for item in OBJECTS if item["type"] == "warehouse")

        print("Seed completed:")
        print(f"  departments: {len(DEPARTMENTS)}")
        print(f"  users: {users_count}")
        print(f"  objects: {objects_count} ({plants} plants + {warehouses} warehouses)")
        print("  other tables: not seeded")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
