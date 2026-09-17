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
    Department,
    Event,
    Normative,
    Object,
    Product,
    ProductionRequest,
    Request,
    RequestItem,
    RequestItemHistory,
    Session,
    SyncMetadata,
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
        await connection.execute(text("""
                DO $$
                BEGIN
                    ALTER TABLE request_items
                        ALTER COLUMN quantity_requested TYPE NUMERIC(12, 6);
                    ALTER TABLE request_items
                        ALTER COLUMN quantity_approved TYPE NUMERIC(12, 6);
                    ALTER TABLE request_item_history
                        ALTER COLUMN old_value TYPE NUMERIC(12, 6);
                EXCEPTION
                    WHEN undefined_table THEN NULL;
                END $$;
                """))
        await connection.execute(text("DROP VIEW IF EXISTS deficit_view"))
        await connection.execute(text("DROP VIEW IF EXISTS normatives_on_date"))
        await connection.execute(
            text("DROP MATERIALIZED VIEW IF EXISTS mv_normative_daily")
        )
        await connection.execute(text("""
                DO $$
                BEGIN
                    ALTER TABLE production_request_items
                        ALTER COLUMN quantity TYPE NUMERIC(16, 6);
                    ALTER TABLE normatives
                        ALTER COLUMN quantity TYPE NUMERIC(16, 6);
                EXCEPTION
                    WHEN undefined_table THEN NULL;
                END $$;
                """))
        await connection.execute(text("""
                CREATE OR REPLACE VIEW normatives_on_date AS
                SELECT
                    n.warehouse_code,
                    o.name AS warehouse_name,
                    n.product_code,
                    p.name AS product_name,
                    n.quantity,
                    n.unit,
                    n.client_name,
                    n.expiry_date,
                    n.category,
                    n.created_at,
                    (
                        SELECT SUM(n2.quantity)
                        FROM normatives n2
                        WHERE n2.warehouse_code = n.warehouse_code
                          AND n2.product_code = n.product_code
                          AND n2.created_at::date <= CURRENT_DATE
                          AND n2.expiry_date >= CURRENT_DATE
                          AND n2.deleted_at IS NULL
                    ) AS total_normative_on_date
                FROM normatives n
                JOIN objects o ON n.warehouse_code = o.code
                JOIN products p ON n.product_code = p.code
                WHERE n.deleted_at IS NULL
                """))
        await connection.execute(text("""
                CREATE OR REPLACE VIEW deficit_view AS
                SELECT
                    n.warehouse_code,
                    o.name AS warehouse_name,
                    n.product_code,
                    p.name AS product_name,
                    p.category,
                    n.quantity AS normative_quantity,
                    n.quantity
                        * CASE p.category
                            WHEN 'A' THEN COALESCE(prm.category_a, 1)
                            WHEN 'B' THEN COALESCE(prm.category_b, 1.5)
                            WHEN 'C' THEN COALESCE(prm.category_c, 2)
                            ELSE 1
                          END
                        * CASE
                            WHEN o.long_distance
                            THEN COALESCE(prm.remote_warehouse, 1.5)
                            ELSE 1
                          END
                        AS requirement,
                    n.unit AS normative_unit,
                    COALESCE(ab.available, 0) AS available,
                    COALESCE(ab.plan, 0) AS plan,
                    COALESCE(ab.unit, 'шт') AS fact_unit,
                    (
                        n.quantity
                        * CASE p.category
                            WHEN 'A' THEN COALESCE(prm.category_a, 1)
                            WHEN 'B' THEN COALESCE(prm.category_b, 1.5)
                            WHEN 'C' THEN COALESCE(prm.category_c, 2)
                            ELSE 1
                          END
                        * CASE
                            WHEN o.long_distance
                            THEN COALESCE(prm.remote_warehouse, 1.5)
                            ELSE 1
                          END
                        - COALESCE(ab.plan, 0)
                    ) AS deficit,
                    n.expiry_date,
                    n.client_name,
                    CASE
                        WHEN (
                            n.quantity
                            * CASE p.category
                                WHEN 'A' THEN COALESCE(prm.category_a, 1)
                                WHEN 'B' THEN COALESCE(prm.category_b, 1.5)
                                WHEN 'C' THEN COALESCE(prm.category_c, 2)
                                ELSE 1
                              END
                            * CASE
                                WHEN o.long_distance
                                THEN COALESCE(prm.remote_warehouse, 1.5)
                                ELSE 1
                              END
                            - COALESCE(ab.plan, 0)
                        ) > 0 THEN 'warning'
                        ELSE 'ok'
                    END AS status
                FROM normatives n
                JOIN objects o ON n.warehouse_code = o.code
                JOIN products p ON n.product_code = p.code
                LEFT JOIN params prm ON prm.id = 1
                LEFT JOIN available_balances ab
                    ON n.warehouse_code = ab.warehouse_code
                    AND n.product_code = ab.product_code
                WHERE n.deleted_at IS NULL
                  AND n.expiry_date >= CURRENT_DATE
                  AND (
                        n.quantity
                        * CASE p.category
                            WHEN 'A' THEN COALESCE(prm.category_a, 1)
                            WHEN 'B' THEN COALESCE(prm.category_b, 1.5)
                            WHEN 'C' THEN COALESCE(prm.category_c, 2)
                            ELSE 1
                          END
                        * CASE
                            WHEN o.long_distance
                            THEN COALESCE(prm.remote_warehouse, 1.5)
                            ELSE 1
                          END
                        - COALESCE(ab.plan, 0)
                      ) > 0
                """))
        await connection.execute(
            text("DROP MATERIALIZED VIEW IF EXISTS mv_normative_daily")
        )
        await connection.execute(
            text(
                """
                CREATE MATERIALIZED VIEW mv_normative_daily AS
                SELECT
                    n.created_at::date AS snapshot_date,
                    n.warehouse_code,
                    o.name AS warehouse_name,
                    n.product_code,
                    p.name AS product_name,
                    p.category,
                    SUM(n.quantity) AS total_normative,
                    COUNT(DISTINCT n.id) AS count_active
                FROM normatives n
                JOIN objects o ON n.warehouse_code = o.code
                JOIN products p ON n.product_code = p.code
                WHERE n.deleted_at IS NULL
                  AND n.expiry_date >= CURRENT_DATE
                GROUP BY
                    n.created_at::date,
                    n.warehouse_code,
                    o.name,
                    n.product_code,
                    p.name,
                    p.category
                """
            )
        )
        await connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_mv_normative_daily
                    ON mv_normative_daily(
                        snapshot_date, warehouse_code, product_code
                    )
                """
            )
        )
        await connection.execute(
            text(
                """
                CREATE OR REPLACE FUNCTION refresh_mv_normative_daily_job()
                RETURNS void AS $$
                BEGIN
                    REFRESH MATERIALIZED VIEW mv_normative_daily;
                END;
                $$ LANGUAGE plpgsql;
                """
            )
        )
        await connection.execute(
            text(
                """
                CREATE OR REPLACE FUNCTION trigger_refresh_mv_normative_daily()
                RETURNS trigger AS $$
                BEGIN
                    REFRESH MATERIALIZED VIEW mv_normative_daily;
                    RETURN NULL;
                END;
                $$ LANGUAGE plpgsql;
                """
            )
        )
        await connection.execute(
            text(
                """
                DROP TRIGGER IF EXISTS trg_refresh_mv_normative_daily_on_balances
                    ON available_balances
                """
            )
        )
        await connection.execute(
            text(
                """
                CREATE TRIGGER trg_refresh_mv_normative_daily_on_balances
                AFTER INSERT OR UPDATE OR DELETE ON available_balances
                FOR EACH STATEMENT
                EXECUTE FUNCTION trigger_refresh_mv_normative_daily()
                """
            )
        )
        await connection.execute(text("DROP INDEX IF EXISTS idx_products_gtin"))
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
            text("ALTER TABLE products DROP CONSTRAINT IF EXISTS products_gtin_key")
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
                "ALTER TABLE objects "
                "ADD COLUMN IF NOT EXISTS long_distance BOOLEAN DEFAULT false"
            )
        )
        await connection.execute(
            text("UPDATE objects SET long_distance = false WHERE long_distance IS NULL")
        )
        await connection.execute(text("""
                CREATE TABLE IF NOT EXISTS departments (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    name TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT true,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    deleted_at TIMESTAMP WITH TIME ZONE
                )
                """))
        await connection.execute(
            text("ALTER TABLE users " "ADD COLUMN IF NOT EXISTS department_id UUID")
        )
        await connection.execute(
            text("ALTER TABLE requests " "ADD COLUMN IF NOT EXISTS department_id UUID")
        )
        await connection.execute(
            text("ALTER TABLE normatives ALTER COLUMN request_id DROP NOT NULL")
        )
        await connection.execute(
            text(
                "ALTER TABLE normatives "
                "ADD COLUMN IF NOT EXISTS production_request_item_id UUID"
            )
        )
        await connection.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint
                        WHERE conname = 'fk_normatives_production_request_item_id'
                    ) THEN
                        ALTER TABLE normatives
                        ADD CONSTRAINT fk_normatives_production_request_item_id
                        FOREIGN KEY (production_request_item_id)
                        REFERENCES production_request_items(id)
                        ON DELETE CASCADE;
                    END IF;
                END $$;
                """))
        await connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS "
                "uq_normatives_production_request_item_id "
                "ON normatives(production_request_item_id)"
            )
        )
        await connection.execute(
            text("DROP TRIGGER IF EXISTS create_normative_on_approve ON requests")
        )
        await connection.execute(
            text("ALTER TABLE normatives DROP CONSTRAINT IF EXISTS ck_normatives_unit")
        )
        await connection.execute(
            text(
                "ALTER TABLE normatives ADD CONSTRAINT ck_normatives_unit "
                "CHECK (unit IN ('шт', 'кг', 'т'))"
            )
        )
        await connection.execute(
            text(
                "ALTER TABLE objects "
                "DROP CONSTRAINT IF EXISTS objects_erp_plant_code_key"
            )
        )
        await connection.execute(
            text(
                "ALTER TABLE objects "
                "DROP CONSTRAINT IF EXISTS objects_erp_warehouse_code_key"
            )
        )
        await connection.execute(
            text("DROP INDEX IF EXISTS objects_erp_plant_code_key")
        )
        await connection.execute(
            text("DROP INDEX IF EXISTS objects_erp_warehouse_code_key")
        )
        await connection.execute(text("DROP INDEX IF EXISTS uq_objects_erp_plant_code"))
        await connection.execute(
            text("DROP INDEX IF EXISTS uq_objects_erp_warehouse_code")
        )
        await connection.execute(text("DROP INDEX IF EXISTS uq_objects_loading_point"))
        await connection.execute(
            text(
                "CREATE UNIQUE INDEX uq_objects_loading_point "
                "ON objects(loading_point) "
                "WHERE loading_point IS NOT NULL AND deleted_at IS NULL"
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
        await connection.execute(text("""
                DO $$
                BEGIN
                    INSERT INTO params (id)
                    VALUES (1)
                    ON CONFLICT (id) DO NOTHING;
                EXCEPTION
                    WHEN undefined_table THEN NULL;
                END $$;
                """))
        await connection.execute(text("""
                DO $$
                BEGIN
                    ALTER TABLE params
                        DROP CONSTRAINT IF EXISTS params_last_modified_by_fkey;
                EXCEPTION
                    WHEN undefined_table THEN NULL;
                    WHEN duplicate_object THEN NULL;
                END $$;
                """))
        await connection.execute(text("""
                DO $$
                BEGIN
                    UPDATE params
                    SET category_a = 1.0,
                        category_b = 1.5,
                        category_c = 2.0,
                        remote_warehouse = 1.5,
                        pallet_multiple = false,
                        last_modified_by = NULL,
                        last_modified_at = NULL
                    WHERE id = 1;
                EXCEPTION
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
    department = "Тесты"
    auth_user = AuthUser(
        id=uuid.uuid4(),
        username=f"user_{suffix}",
        password=password,
        role=role,
        email=f"user_{suffix}@company.ru",
        full_name=f"Test User {suffix}",
    )
    async with AsyncSessionLocal() as session:
        department_id = None
        if department:
            existing = await session.scalar(
                select(Department).where(Department.name == department)
            )
            if existing is None:
                dept = Department(name=department, is_active=True)
                session.add(dept)
                await session.flush()
                department_id = dept.id
            else:
                department_id = existing.id
        session.add(
            User(
                id=auth_user.id,
                username=auth_user.username,
                email=auth_user.email,
                password_hash=hash_password(password),
                full_name=auth_user.full_name,
                role=role,
                department=department,
                department_id=department_id,
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
            update(SyncMetadata)
            .where(SyncMetadata.last_balances_sync_by == user_id)
            .values(last_balances_sync_by=None)
        )
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
        await session.execute(
            delete(ProductionRequest).where(ProductionRequest.uploaded_by == user_id)
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
                erp_plant_code=2401,
                erp_warehouse_code="F005",
                is_active=True,
            ),
            Object(
                code=2002,
                name="Склад Владивосток",
                city="Владивосток",
                region="Приморский край",
                type="warehouse",
                erp_plant_code=2402,
                erp_warehouse_code="F006",
                is_active=True,
            ),
        ]
        for item in plants + warehouses:
            existing = await session.get(Object, item.code)
            if existing is None:
                session.add(item)
                continue
            existing.deleted_at = None
            existing.name = item.name
            existing.city = item.city
            existing.region = item.region
            existing.type = item.type
            existing.is_active = True
            if item.erp_plant_code is not None:
                existing.erp_plant_code = item.erp_plant_code
            if item.erp_warehouse_code is not None:
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
            existing = await session.get(Product, item.code)
            if existing is None:
                session.add(item)
                continue
            existing.deleted_at = None
            existing.name = item.name
            existing.category = item.category
            existing.plant_id = item.plant_id
            existing.weight_kg = item.weight_kg
            existing.monthly_consumption = item.monthly_consumption
            existing.pallet_qty = None
            existing.is_active = True
        await session.commit()
    return {
        "product_code": 10001,
        "product_code_2": 10002,
        "warehouse_code": 2001,
        "warehouse_code_2": 2002,
        "plant_code": 1001,
        "erp_plant_code": 2401,
        "erp_plant_code_2": 2402,
        "erp_warehouse_code": "F005",
        "erp_warehouse_code_2": "F006",
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
