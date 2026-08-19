import uuid
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from decimal import Decimal

import pytest
from fastapi import Depends
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from app.api.deps import require_roles
from app.core.database import AsyncSessionLocal, check_database_connection, engine
from app.core.security import hash_password
from app.main import app
from app.models import (
    Base,
    Event,
    Object,
    Product,
    Request,
    RequestItem,
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


async def _delete_user(user_id: uuid.UUID) -> None:
    async with AsyncSessionLocal() as session:
        request_ids = (
            await session.scalars(
                select(Request.id).where(
                    (Request.initiator_id == user_id)
                    | (Request.pp_approved_by == user_id)
                    | (Request.economy_approved_by == user_id)
                )
            )
        ).all()
        if request_ids:
            await session.execute(
                delete(Event).where(Event.request_id.in_(request_ids))
            )
            await session.execute(
                delete(RequestItem).where(RequestItem.request_id.in_(request_ids))
            )
            await session.execute(delete(Request).where(Request.id.in_(request_ids)))
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
                is_active=True,
            ),
            Object(
                code=1002,
                name="Завод Екатеринбургский",
                city="Екатеринбург",
                region="Свердловская область",
                type="plant",
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
                is_active=True,
            ),
            Object(
                code=2002,
                name="Склад Владивосток",
                city="Владивосток",
                region="Приморский край",
                type="warehouse",
                is_active=True,
            ),
        ]
        for item in plants + warehouses:
            if await session.get(Object, item.code) is None:
                session.add(item)
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
        await session.execute(delete(Event).where(Event.request_id == request_id))
        await session.execute(
            delete(RequestItem).where(RequestItem.request_id == request_id)
        )
        await session.execute(delete(Request).where(Request.id == request_id))
        await session.commit()
