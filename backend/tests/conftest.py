import uuid
from collections.abc import AsyncGenerator
from dataclasses import dataclass

import pytest
from fastapi import Depends
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

from app.api.deps import require_roles
from app.core.database import AsyncSessionLocal, check_database_connection, engine
from app.core.security import hash_password
from app.main import app
from app.models import Base, Session, User

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
