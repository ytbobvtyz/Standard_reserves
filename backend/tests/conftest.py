import uuid
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from decimal import Decimal

import pytest
from fastapi import Depends
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select, text, update

from app.api.deps import require_roles
from app.core.database import AsyncSessionLocal, check_database_connection, engine
from app.core.security import hash_password
from app.main import app
from app.models import (
    AuditLog,
    Base,
    Event,
    Normative,
    Object,
    Product,
    Request,
    RequestItem,
    RequestItemHistory,
    Session,
    User,
)

DEFAULT_PASSWORD = "password"


@dataclass
class AuthUser:
    id: uuid.UUID
    username: str
    password: str
    role: str
    email: str
    full_name: str


@app.get("/api/v1/_rbac/pp")
async def rbac_pp_only(user: User = Depends(require_roles("pp"))):
    return {"status": "success", "data": {"role": user.role}}


@pytest.fixture
async def db_ready() -> AsyncGenerator[None, None]:
    await check_database_connection()
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        await connection.execute(
            text("ALTER TABLE requests " "ADD COLUMN IF NOT EXISTS executed_by UUID")
        )
        await connection.execute(
            text("ALTER TABLE requests ADD COLUMN IF NOT EXISTS order_number TEXT")
        )
        await connection.execute(
            text(
                "ALTER TABLE requests " "ADD COLUMN IF NOT EXISTS executed_comment TEXT"
            )
        )
        await connection.execute(
            text("ALTER TABLE products " "ADD COLUMN IF NOT EXISTS gtin VARCHAR(13)")
        )
        await connection.execute(
            text(
                "ALTER TABLE products "
                "ADD COLUMN IF NOT EXISTS mark_control BOOLEAN DEFAULT false"
            )
        )
        await connection.execute(
            text(
                "ALTER TABLE products " "ADD COLUMN IF NOT EXISTS last_modified_by UUID"
            )
        )
        await connection.execute(
            text(
                "ALTER TABLE products "
                "ADD COLUMN IF NOT EXISTS last_modified_at "
                "TIMESTAMP WITH TIME ZONE"
            )
        )
        await connection.execute(
            text("ALTER TABLE products " "ALTER COLUMN mark_control SET DEFAULT false")
        )
        await connection.execute(
            text("UPDATE products SET mark_control = false WHERE mark_control IS NULL")
        )
        await connection.execute(
            text("DROP INDEX IF EXISTS idx_products_gtin")
        )
        await connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_products_gtin "
                "ON products(gtin) WHERE gtin IS NOT NULL"
            )
        )
        await connection.execute(
            text(
                "ALTER TABLE products "
                "DROP CONSTRAINT IF EXISTS products_parent_code_fkey"
            )
        )
        await connection.execute(
            text(
                "ALTER TABLE products "
                "DROP CONSTRAINT IF EXISTS products_children_code_fkey"
            )
        )
        await connection.execute(
            text(
                "ALTER TABLE products DROP CONSTRAINT IF EXISTS products_gtin_key"
            )
        )
        await connection.execute(
            text(
                "ALTER TABLE objects " "ADD COLUMN IF NOT EXISTS last_modified_by UUID"
            )
        )
        await connection.execute(
            text(
                "ALTER TABLE objects "
                "ADD COLUMN IF NOT EXISTS last_modified_at "
                "TIMESTAMP WITH TIME ZONE"
            )
        )
        await connection.execute(
            text(
                "ALTER TABLE objects " "ADD COLUMN IF NOT EXISTS erp_plant_code INTEGER"
            )
        )
        await connection.execute(
            text(
                "ALTER TABLE objects "
                "ADD COLUMN IF NOT EXISTS erp_warehouse_code VARCHAR(4)"
            )
        )
        await connection.execute(
            text(
                "ALTER TABLE objects ADD COLUMN IF NOT EXISTS loading_point VARCHAR(4)"
            )
        )
        await connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_objects_erp_plant_code "
                "ON objects(erp_plant_code)"
            )
        )
        await connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_objects_erp_warehouse_code "
                "ON objects(erp_warehouse_code)"
            )
        )
        await connection.execute(text("""
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema = 'public'
                          AND table_name = 'available_balances'
                          AND column_name = 'quantity'
                    ) AND NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema = 'public'
                          AND table_name = 'available_balances'
                          AND column_name = 'available'
                    ) THEN
                        ALTER TABLE available_balances
                            RENAME COLUMN quantity TO available;
                    END IF;
                END $$;
                """))
        await connection.execute(
            text(
                "ALTER TABLE available_balances "
                "ADD COLUMN IF NOT EXISTS plan DECIMAL(12,2) NOT NULL DEFAULT 0"
            )
        )
        await connection.execute(text("""
                DO $$
                BEGIN
                    ALTER TABLE available_balances
                        DROP CONSTRAINT IF EXISTS available_balances_unit_check;
                    ALTER TABLE available_balances
                        DROP CONSTRAINT IF EXISTS ck_available_balances_unit;
                    ALTER TABLE available_balances
                        ADD CONSTRAINT ck_available_balances_unit
                        CHECK (unit IN ('шт', 'т', 'ШТ', 'КГ'));
                EXCEPTION
                    WHEN duplicate_object THEN NULL;
                    WHEN undefined_table THEN NULL;
                END $$;
                """))
    yield


@pytest.fixture
async def client(db_ready: None) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client


async def _create_user(
    *,
    role: str = "commercial",
    is_active: bool = True,
    password: str = DEFAULT_PASSWORD,
) -> AuthUser:
    suffix = uuid.uuid4().hex[:10]
    auth_user = AuthUser(
        id=uuid.uuid4(),
        username=f"user_{suffix}",
        password=password,
        role=role,
        email=f"user_{suffix}@company.ru",
        full_name=f"Test User {suffix}",
    )
    async with AsyncSessionLocal() as session:
        session.add(
            User(
                id=auth_user.id,
                username=auth_user.username,
                email=auth_user.email,
                password_hash=hash_password(password),
                full_name=auth_user.full_name,
                role=role,
                department="Тесты",
                is_active=is_active,
            )
        )
        await session.commit()
    return auth_user


async def _purge_requests(session, request_ids: list[uuid.UUID]) -> None:
    if not request_ids:
        return
    item_ids = (
        await session.scalars(
            select(RequestItem.id).where(RequestItem.request_id.in_(request_ids))
        )
    ).all()
    if item_ids:
        await session.execute(
            delete(RequestItemHistory).where(
                RequestItemHistory.request_item_id.in_(item_ids)
            )
        )
    await session.execute(
        delete(Normative).where(Normative.request_id.in_(request_ids))
    )
    await session.execute(delete(Event).where(Event.request_id.in_(request_ids)))
    await session.execute(
        delete(RequestItem).where(RequestItem.request_id.in_(request_ids))
    )
    await session.execute(delete(Request).where(Request.id.in_(request_ids)))


async def _delete_user(user_id: uuid.UUID) -> None:
    async with AsyncSessionLocal() as session:
        request_ids = (
            await session.scalars(
                select(Request.id).where(
                    (Request.initiator_id == user_id)
                    | (Request.pp_approved_by == user_id)
                    | (Request.economy_approved_by == user_id)
                    | (Request.executed_by == user_id)
                )
            )
        ).all()
        await session.execute(
            delete(RequestItemHistory).where(RequestItemHistory.changed_by == user_id)
        )
        await session.execute(delete(AuditLog).where(AuditLog.changed_by == user_id))
        await session.execute(
            update(Product)
            .where(Product.last_modified_by == user_id)
            .values(last_modified_by=None)
        )
        await session.execute(
            update(Object)
            .where(Object.last_modified_by == user_id)
            .values(last_modified_by=None)
        )
        await _purge_requests(session, list(request_ids))
        await session.execute(delete(Session).where(Session.user_id == user_id))
        await session.execute(delete(User).where(User.id == user_id))
        await session.commit()


@pytest.fixture
async def test_user(db_ready: None) -> AsyncGenerator[AuthUser, None]:
    user = await _create_user(role="commercial")
    yield user
    await _delete_user(user.id)


@pytest.fixture
async def inactive_user(db_ready: None) -> AsyncGenerator[AuthUser, None]:
    user = await _create_user(role="commercial", is_active=False)
    yield user
    await _delete_user(user.id)


@pytest.fixture
async def pp_user(db_ready: None) -> AsyncGenerator[AuthUser, None]:
    user = await _create_user(role="pp")
    yield user
    await _delete_user(user.id)


@pytest.fixture
async def economist_user(db_ready: None) -> AsyncGenerator[AuthUser, None]:
    user = await _create_user(role="economist")
    yield user
    await _delete_user(user.id)


@pytest.fixture
async def logistics_user(db_ready: None) -> AsyncGenerator[AuthUser, None]:
    user = await _create_user(role="logistics")
    yield user
    await _delete_user(user.id)


@pytest.fixture
async def guest_user(db_ready: None) -> AsyncGenerator[AuthUser, None]:
    user = await _create_user(role="guest")
    yield user
    await _delete_user(user.id)


@pytest.fixture
async def other_user(db_ready: None) -> AsyncGenerator[AuthUser, None]:
    user = await _create_user(role="commercial")
    yield user
    await _delete_user(user.id)


@pytest.fixture
async def catalog(db_ready: None) -> dict[str, int]:
    async with AsyncSessionLocal() as session:
        plants = [
            Object(
                code=1001,
                name="Завод Московский",
                city="Москва",
                region="Московская область",
                type="plant",
                erp_plant_code=2401,
                is_active=True,
            ),
            Object(
                code=1002,
                name="Завод Екатеринбургский",
                city="Екатеринбург",
                region="Свердловская область",
                type="plant",
                erp_plant_code=2402,
                is_active=True,
            ),
        ]
        warehouses = [
            Object(
                code=2001,
                name="Склад Ростов",
                city="Ростов-на-Дону",
                region="Ростовская область",
                type="warehouse",
                erp_warehouse_code="F005",
                is_active=True,
            ),
            Object(
                code=2002,
                name="Склад Владивосток",
                city="Владивосток",
                region="Приморский край",
                type="warehouse",
                erp_warehouse_code="F006",
                is_active=True,
            ),
        ]
        for item in plants + warehouses:
            existing = await session.get(Object, item.code)
            if existing is None:
                session.add(item)
                continue
            if item.type == "plant" and existing.erp_plant_code is None:
                existing.erp_plant_code = item.erp_plant_code
            if item.type == "warehouse" and existing.erp_warehouse_code is None:
                existing.erp_warehouse_code = item.erp_warehouse_code
        await session.flush()

        products = [
            Product(
                code=10001,
                name="Подшипник 6204ZZ",
                category="A",
                plant_id=1001,
                weight_kg=Decimal("0.2500"),
                monthly_consumption=Decimal("1000.00"),
                is_active=True,
            ),
            Product(
                code=10002,
                name="Корпус чугунный 200мм",
                category="B",
                plant_id=1002,
                weight_kg=Decimal("2.5000"),
                monthly_consumption=Decimal("500.00"),
                is_active=True,
            ),
        ]
        for item in products:
            if await session.get(Product, item.code) is None:
                session.add(item)
        await session.commit()
    return {
        "product_code": 10001,
        "product_code_2": 10002,
        "warehouse_code": 2001,
        "warehouse_code_2": 2002,
        "plant_code": 1001,
        "erp_plant_code": 2401,
        "erp_warehouse_code": "F005",
    }


async def login_token(client: AsyncClient, user: AuthUser) -> str:
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": user.username, "password": user.password},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]["access_token"]


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def delete_request(request_id: uuid.UUID) -> None:
    async with AsyncSessionLocal() as session:
        await _purge_requests(session, [request_id])
        await session.commit()
