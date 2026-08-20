"""Seed reference data for local development (Stage 1)."""

from __future__ import annotations

import asyncio
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.security import hash_password
from app.models import (
    AvailableBalance,
    Normative,
    Object,
    Product,
    Request,
    RequestItem,
    User,
)

PLANTS = [
    {
        "code": 1001,
        "name": "Завод Московский",
        "city": "Москва",
        "region": "Московская область",
        "type": "plant",
    },
    {
        "code": 1002,
        "name": "Завод Екатеринбургский",
        "city": "Екатеринбург",
        "region": "Свердловская область",
        "type": "plant",
    },
    {
        "code": 1003,
        "name": "Завод Новосибирский",
        "city": "Новосибирск",
        "region": "Новосибирская область",
        "type": "plant",
    },
]

WAREHOUSES = [
    {
        "code": 2001,
        "name": "Склад Ростов",
        "city": "Ростов-на-Дону",
        "region": "Ростовская область",
        "type": "warehouse",
    },
    {
        "code": 2002,
        "name": "Склад Владивосток",
        "city": "Владивосток",
        "region": "Приморский край",
        "type": "warehouse",
    },
    {
        "code": 2003,
        "name": "Склад Казань",
        "city": "Казань",
        "region": "Республика Татарстан",
        "type": "warehouse",
    },
    {
        "code": 2004,
        "name": "Склад Краснодар",
        "city": "Краснодар",
        "region": "Краснодарский край",
        "type": "warehouse",
    },
    {
        "code": 2005,
        "name": "Склад Санкт-Петербург",
        "city": "Санкт-Петербург",
        "region": "Санкт-Петербург",
        "type": "warehouse",
    },
]

PRODUCTS = [
    {
        "code": 10001,
        "name": "Подшипник 6204ZZ",
        "category": "A",
        "plant_id": 1001,
        "weight_kg": Decimal("0.2500"),
        "monthly_consumption": Decimal("1000.00"),
        "children_code": 10004,
    },
    {
        "code": 10002,
        "name": "Корпус чугунный 200мм",
        "category": "B",
        "plant_id": 1002,
        "weight_kg": Decimal("2.5000"),
        "monthly_consumption": Decimal("500.00"),
    },
    {
        "code": 10003,
        "name": "Вал приводной 500мм",
        "category": "C",
        "plant_id": 1003,
        "weight_kg": Decimal("8.2000"),
        "monthly_consumption": Decimal("120.00"),
    },
    {
        "code": 10004,
        "name": "Подшипник 6204ZZ-NEW",
        "category": "A",
        "plant_id": 1001,
        "weight_kg": Decimal("0.2550"),
        "monthly_consumption": Decimal("800.00"),
        "parent_code": 10001,
    },
    {
        "code": 10005,
        "name": "Манжета 50x70x10",
        "category": "B",
        "plant_id": 1002,
        "weight_kg": Decimal("0.0450"),
        "monthly_consumption": Decimal("2000.00"),
    },
    {
        "code": 10006,
        "name": "Крышка подшипника",
        "category": "C",
        "plant_id": 1001,
        "second_plant_id": 1002,
        "weight_kg": Decimal("0.1800"),
        "monthly_consumption": Decimal("400.00"),
    },
    {
        "code": 10007,
        "name": "Муфта зубчатая",
        "category": "A",
        "plant_id": 1002,
        "weight_kg": Decimal("3.1000"),
        "monthly_consumption": Decimal("150.00"),
    },
    {
        "code": 10008,
        "name": "Болт М16х80",
        "category": "B",
        "plant_id": 1003,
        "weight_kg": Decimal("0.1200"),
        "monthly_consumption": Decimal("5000.00"),
    },
    {
        "code": 10009,
        "name": "Редуктор Ц2У-200",
        "category": "C",
        "plant_id": 1002,
        "third_plant_id": 1003,
        "weight_kg": Decimal("45.0000"),
        "monthly_consumption": Decimal("20.00"),
    },
    {
        "code": 10010,
        "name": "Сальник 80x100x12",
        "category": "A",
        "plant_id": 1003,
        "weight_kg": Decimal("0.0550"),
        "monthly_consumption": Decimal("1500.00"),
    },
]

USERS = [
    {
        "id": uuid.UUID("11111111-1111-1111-1111-111111111111"),
        "username": "commercial",
        "email": "commercial@company.ru",
        "full_name": "Иванов Иван",
        "role": "commercial",
        "department": "Коммерческий отдел",
    },
    {
        "id": uuid.UUID("22222222-2222-2222-2222-222222222222"),
        "username": "pp",
        "email": "pp@company.ru",
        "full_name": "Петров Петр",
        "role": "pp",
        "department": "Планирование производства",
    },
    {
        "id": uuid.UUID("33333333-3333-3333-3333-333333333333"),
        "username": "economist",
        "email": "economist@company.ru",
        "full_name": "Сидоров Сидор",
        "role": "economist",
        "department": "Экономический отдел",
    },
    {
        "id": uuid.UUID("44444444-4444-4444-4444-444444444444"),
        "username": "logistics",
        "email": "logistics@company.ru",
        "full_name": "Кузнецов Кузьма",
        "role": "logistics",
        "department": "Логистика",
    },
    {
        "id": uuid.UUID("55555555-5555-5555-5555-555555555555"),
        "username": "guest",
        "email": "guest@company.ru",
        "full_name": "Смирнов Гость",
        "role": "guest",
        "department": None,
    },
]

SEED_PASSWORD = "password"
SEED_REQUEST_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
SEED_ONE_TIME_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
SEED_CLIENT = "ООО «Ромашка»"
SEED_ONE_TIME_CLIENT = "ООО «Тюльпан»"

SEED_NORMATIVES = [
    {
        "product_code": 10001,
        "warehouse_code": 2001,
        "quantity": Decimal("1000"),
        "unit": "шт",
        "category": "A",
    },
    {
        "product_code": 10002,
        "warehouse_code": 2002,
        "quantity": Decimal("500"),
        "unit": "шт",
        "category": "B",
    },
    {
        "product_code": 10005,
        "warehouse_code": 2001,
        "quantity": Decimal("500"),
        "unit": "шт",
        "category": "B",
    },
]

SEED_BALANCES = [
    {"warehouse_code": 2001, "product_code": 10001, "quantity": Decimal("600")},
    {"warehouse_code": 2002, "product_code": 10002, "quantity": Decimal("200")},
    {"warehouse_code": 2001, "product_code": 10005, "quantity": Decimal("450")},
    {"warehouse_code": 2003, "product_code": 10003, "quantity": Decimal("40")},
]


async def _upsert_object(session: AsyncSession, payload: dict) -> None:
    existing = await session.get(Object, payload["code"])
    if existing is None:
        session.add(Object(**payload, is_active=True))


async def _upsert_product(session: AsyncSession, payload: dict) -> None:
    data = dict(payload)
    data.pop("parent_code", None)
    data.pop("children_code", None)
    existing = await session.get(Product, data["code"])
    if existing is None:
        session.add(Product(**data, is_active=True))


async def _upsert_logistics_demo(session: AsyncSession) -> None:
    commercial = await session.get(User, USERS[0]["id"])
    if commercial is None:
        return

    request = await session.get(Request, SEED_REQUEST_ID)
    if request is None:
        session.add(
            Request(
                id=SEED_REQUEST_ID,
                request_type="normative",
                status="active",
                client_name=SEED_CLIENT,
                initiator_id=commercial.id,
                expiry_date=date(2026, 12, 31),
            )
        )
        await session.flush()
    else:
        request.status = "active"
        request.client_name = SEED_CLIENT
        request.expiry_date = date(2026, 12, 31)
        request.deleted_at = None

    existing_items = {
        (item.product_code, item.warehouse_code): item
        for item in (
            await session.scalars(
                select(RequestItem).where(RequestItem.request_id == SEED_REQUEST_ID)
            )
        ).all()
    }
    for item in SEED_NORMATIVES:
        key = (item["product_code"], item["warehouse_code"])
        if key in existing_items:
            continue
        session.add(
            RequestItem(
                request_id=SEED_REQUEST_ID,
                product_code=item["product_code"],
                warehouse_code=item["warehouse_code"],
                quantity_requested=item["quantity"],
                quantity_approved=item["quantity"],
                unit=item["unit"],
            )
        )

    existing_normatives = {
        (item.product_code, item.warehouse_code): item
        for item in (
            await session.scalars(
                select(Normative).where(
                    Normative.request_id == SEED_REQUEST_ID,
                    Normative.deleted_at.is_(None),
                )
            )
        ).all()
    }
    for item in SEED_NORMATIVES:
        key = (item["product_code"], item["warehouse_code"])
        current = existing_normatives.get(key)
        if current is None:
            session.add(
                Normative(
                    request_id=SEED_REQUEST_ID,
                    product_code=item["product_code"],
                    warehouse_code=item["warehouse_code"],
                    quantity=item["quantity"],
                    unit=item["unit"],
                    client_name=SEED_CLIENT,
                    expiry_date=date(2026, 12, 31),
                    category=item["category"],
                )
            )
            continue
        current.quantity = item["quantity"]
        current.unit = item["unit"]
        current.client_name = SEED_CLIENT
        current.expiry_date = date(2026, 12, 31)
        current.category = item["category"]
        current.deleted_at = None

    for item in SEED_BALANCES:
        current = await session.get(
            AvailableBalance, (item["warehouse_code"], item["product_code"])
        )
        if current is None:
            session.add(
                AvailableBalance(
                    warehouse_code=item["warehouse_code"],
                    product_code=item["product_code"],
                    quantity=item["quantity"],
                    unit="шт",
                    source="manual",
                )
            )
            continue
        current.quantity = item["quantity"]
        current.unit = "шт"
        current.source = "manual"


async def _upsert_one_time_demo(session: AsyncSession) -> None:
    commercial = await session.get(User, USERS[0]["id"])
    if commercial is None:
        return

    request = await session.get(Request, SEED_ONE_TIME_ID)
    if request is None:
        session.add(
            Request(
                id=SEED_ONE_TIME_ID,
                request_type="one_time",
                status="approved",
                client_name=SEED_ONE_TIME_CLIENT,
                initiator_id=commercial.id,
                initiator_comment="Разовое перемещение для проверки этапа 6",
            )
        )
        await session.flush()
    else:
        if request.status != "executed":
            request.status = "approved"
            request.executed_at = None
            request.executed_by = None
            request.order_number = None
            request.executed_comment = None
        request.client_name = SEED_ONE_TIME_CLIENT
        request.request_type = "one_time"
        request.deleted_at = None

    existing_items = {
        (item.product_code, item.warehouse_code): item
        for item in (
            await session.scalars(
                select(RequestItem).where(RequestItem.request_id == SEED_ONE_TIME_ID)
            )
        ).all()
    }
    item_key = (10001, 2001)
    if item_key not in existing_items:
        session.add(
            RequestItem(
                request_id=SEED_ONE_TIME_ID,
                product_code=10001,
                warehouse_code=2001,
                quantity_requested=Decimal("200"),
                quantity_approved=Decimal("200"),
                unit="шт",
            )
        )


async def _upsert_user(session: AsyncSession, payload: dict) -> None:
    password_hash = hash_password(SEED_PASSWORD)
    existing = await session.get(User, payload["id"])
    if existing is None:
        session.add(User(**payload, password_hash=password_hash, is_active=True))
        return
    existing.password_hash = password_hash
    existing.username = payload["username"]
    existing.email = payload["email"]
    existing.full_name = payload["full_name"]
    existing.role = payload["role"]
    existing.department = payload["department"]
    existing.is_active = True
    existing.deleted_at = None


async def seed() -> None:
    engine = create_async_engine(settings.async_database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        for item in PLANTS + WAREHOUSES:
            await _upsert_object(session, item)
        await session.flush()

        for item in PRODUCTS:
            await _upsert_product(session, item)
        await session.flush()

        for item in PRODUCTS:
            product = await session.get(Product, item["code"])
            if product is None:
                continue
            product.parent_code = item.get("parent_code")
            product.children_code = item.get("children_code")

        for item in USERS:
            await _upsert_user(session, item)

        await _upsert_logistics_demo(session)
        await _upsert_one_time_demo(session)

        await session.commit()

        products_count = len((await session.scalars(select(Product))).all())
        users_count = len((await session.scalars(select(User))).all())
        objects_count = len((await session.scalars(select(Object))).all())
        sample_plant = await session.scalar(
            select(Object).where(Object.type == "plant")
        )
        sample_label = (
            f"{sample_plant.code} {sample_plant.name}" if sample_plant else "-"
        )

        print("Seed completed:")
        print(f"  objects: {objects_count} (3 plants + 5 warehouses)")
        print(f"  products: {products_count}")
        print(f"  users: {users_count}")
        print(f"  sample plant: {sample_label}")
        print("  logistics demo: active normatives + available_balances")
        print("  one-time demo: approved request ООО «Тюльпан»")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
