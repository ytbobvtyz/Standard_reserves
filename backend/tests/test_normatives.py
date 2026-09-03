from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy import delete, select

from app.core.database import AsyncSessionLocal
from app.models.normative import Normative
from app.models.product import Product
from app.models.request import Request
from tests.conftest import AuthUser, auth_header, delete_request, login_token

TEST_PRODUCT_A = 18001
TEST_PRODUCT_B = 18002
TEST_PRODUCT_C = 18003
CLIENT_A = "Тест нормативы Альфа"
CLIENT_B = "Тест нормативы Бета"
CLIENT_EXPIRED = "Тест нормативы Истекший"


async def _cleanup_products(product_codes: list[int]) -> None:
    async with AsyncSessionLocal() as session:
        leftover_ids = (
            await session.scalars(
                select(Request.id).where(
                    Request.client_name.in_([CLIENT_A, CLIENT_B, CLIENT_EXPIRED])
                )
            )
        ).all()
    for request_id in leftover_ids:
        await delete_request(request_id)
    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(Normative).where(Normative.product_code.in_(product_codes))
        )
        await session.execute(delete(Product).where(Product.code.in_(product_codes)))
        await session.commit()


async def _seed_normatives(catalog: dict[str, int], test_user: AuthUser) -> dict:
    request_id = uuid4()
    expired_request_id = uuid4()
    future_request_id = uuid4()
    warehouse_code = catalog["warehouse_code"]
    warehouse_code_2 = catalog["warehouse_code_2"]
    product_codes = [TEST_PRODUCT_A, TEST_PRODUCT_B, TEST_PRODUCT_C]
    await _cleanup_products(product_codes)

    async with AsyncSessionLocal() as session:
        session.add(
            Product(
                code=TEST_PRODUCT_A,
                name="Тестовый подшипник этапа 7",
                category="A",
                plant_id=catalog["plant_code"],
                weight_kg=Decimal("0.2500"),
                monthly_consumption=Decimal("1000.00"),
                is_active=True,
            )
        )
        session.add(
            Product(
                code=TEST_PRODUCT_B,
                name="Тестовый корпус этапа 7",
                category="B",
                plant_id=catalog["plant_code"],
                weight_kg=Decimal("2.5000"),
                monthly_consumption=Decimal("500.00"),
                is_active=True,
            )
        )
        session.add(
            Product(
                code=TEST_PRODUCT_C,
                name="Тестовый вал этапа 7",
                category="C",
                plant_id=catalog["plant_code"],
                weight_kg=Decimal("8.2000"),
                monthly_consumption=Decimal("120.00"),
                is_active=True,
            )
        )
        await session.flush()
        session.add(
            Request(
                id=request_id,
                request_type="normative",
                status="active",
                client_name=CLIENT_A,
                initiator_id=test_user.id,
                expiry_date=date(2026, 12, 31),
            )
        )
        session.add(
            Request(
                id=expired_request_id,
                request_type="normative",
                status="expired",
                client_name=CLIENT_EXPIRED,
                initiator_id=test_user.id,
                expiry_date=date(2026, 1, 15),
            )
        )
        session.add(
            Request(
                id=future_request_id,
                request_type="normative",
                status="active",
                client_name=CLIENT_B,
                initiator_id=test_user.id,
                expiry_date=date(2027, 6, 30),
            )
        )
        session.add(
            Normative(
                request_id=request_id,
                product_code=TEST_PRODUCT_A,
                warehouse_code=warehouse_code,
                quantity=Decimal("1000"),
                unit="шт",
                client_name=CLIENT_A,
                expiry_date=date(2026, 12, 31),
                category="A",
                created_at=datetime(2026, 1, 10, tzinfo=UTC),
            )
        )
        session.add(
            Normative(
                request_id=future_request_id,
                product_code=TEST_PRODUCT_A,
                warehouse_code=warehouse_code,
                quantity=Decimal("400"),
                unit="шт",
                client_name=CLIENT_B,
                expiry_date=date(2027, 6, 30),
                category="A",
                created_at=datetime(2026, 3, 1, tzinfo=UTC),
            )
        )
        session.add(
            Normative(
                request_id=request_id,
                product_code=TEST_PRODUCT_B,
                warehouse_code=warehouse_code_2,
                quantity=Decimal("500"),
                unit="шт",
                client_name=CLIENT_A,
                expiry_date=date(2026, 12, 31),
                category="B",
                created_at=datetime(2026, 2, 1, tzinfo=UTC),
            )
        )
        session.add(
            Normative(
                request_id=expired_request_id,
                product_code=TEST_PRODUCT_C,
                warehouse_code=warehouse_code,
                quantity=Decimal("80"),
                unit="шт",
                client_name=CLIENT_EXPIRED,
                expiry_date=date(2026, 1, 15),
                category="C",
                created_at=datetime(2025, 12, 1, tzinfo=UTC),
            )
        )
        await session.commit()

    return {
        "request_id": request_id,
        "expired_request_id": expired_request_id,
        "future_request_id": future_request_id,
        "warehouse_code": warehouse_code,
        "warehouse_code_2": warehouse_code_2,
    }


async def test_list_current_normatives_paginated(
    client: AsyncClient, test_user: AuthUser, catalog: dict[str, int]
) -> None:
    seeded = await _seed_normatives(catalog, test_user)
    token = await login_token(client, test_user)
    response = await client.get(
        "/api/v1/normatives",
        headers=auth_header(token),
        params={"page": 1, "limit": 1, "client_name": "Тест нормативы"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "success"
    assert len(body["data"]) == 1
    assert body["meta"]["page"] == 1
    assert body["meta"]["limit"] == 1
    assert body["meta"]["total"] >= 2
    item = body["data"][0]
    assert "product_name" in item
    assert "warehouse_name" in item
    assert "quantity" in item
    assert item["expiry_date"] >= date.today().isoformat()

    await delete_request(seeded["request_id"])
    await delete_request(seeded["expired_request_id"])
    await delete_request(seeded["future_request_id"])
    await _cleanup_products([TEST_PRODUCT_A, TEST_PRODUCT_B, TEST_PRODUCT_C])


async def test_list_current_normatives_filters(
    client: AsyncClient, test_user: AuthUser, catalog: dict[str, int]
) -> None:
    seeded = await _seed_normatives(catalog, test_user)
    token = await login_token(client, test_user)
    response = await client.get(
        "/api/v1/normatives",
        headers=auth_header(token),
        params={
            "warehouse_code": catalog["warehouse_code"],
            "product_code": TEST_PRODUCT_A,
            "category": "A",
            "client_name": "Альфа",
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data
    assert all(item["warehouse_code"] == catalog["warehouse_code"] for item in data)
    assert all(item["product_code"] == TEST_PRODUCT_A for item in data)
    assert all(item["category"] == "A" for item in data)
    assert all("Альфа" in item["client_name"] for item in data)
    codes = {item["product_code"] for item in data}
    assert TEST_PRODUCT_C not in codes

    by_name = await client.get(
        "/api/v1/normatives",
        headers=auth_header(token),
        params={"search": "подшипник", "client_name": "Тест нормативы"},
    )
    assert by_name.status_code == 200, by_name.text
    name_codes = {item["product_code"] for item in by_name.json()["data"]}
    assert TEST_PRODUCT_A in name_codes
    assert TEST_PRODUCT_B not in name_codes

    by_code = await client.get(
        "/api/v1/normatives",
        headers=auth_header(token),
        params={"search": str(TEST_PRODUCT_A), "client_name": "Тест нормативы"},
    )
    assert by_code.status_code == 200, by_code.text
    code_matches = by_code.json()["data"]
    assert code_matches
    assert all(item["product_code"] == TEST_PRODUCT_A for item in code_matches)

    await delete_request(seeded["request_id"])
    await delete_request(seeded["expired_request_id"])
    await delete_request(seeded["future_request_id"])
    await _cleanup_products([TEST_PRODUCT_A, TEST_PRODUCT_B, TEST_PRODUCT_C])


async def test_normatives_on_date_groups_and_filters(
    client: AsyncClient, test_user: AuthUser, catalog: dict[str, int]
) -> None:
    seeded = await _seed_normatives(catalog, test_user)
    token = await login_token(client, test_user)
    response = await client.get(
        "/api/v1/normatives/on-date",
        headers=auth_header(token),
        params={"date": "2026-12-31", "warehouse_code": catalog["warehouse_code"]},
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    grouped = next(item for item in data if item["product_code"] == TEST_PRODUCT_A)
    assert grouped["warehouse_code"] == catalog["warehouse_code"]
    assert grouped["total_quantity"] == 1400
    assert grouped["unit"] == "шт"
    clients = {detail["client_name"] for detail in grouped["details"]}
    assert CLIENT_A in clients
    assert CLIENT_B in clients
    detail_a = next(
        detail for detail in grouped["details"] if detail["client_name"] == CLIENT_A
    )
    assert detail_a["request_id"] == str(seeded["request_id"])
    assert detail_a["author_name"] == test_user.full_name
    assert detail_a["expiry_date"] == "2026-12-31"
    product_codes = {item["product_code"] for item in data}
    assert TEST_PRODUCT_C not in product_codes

    expired_slice = await client.get(
        "/api/v1/normatives/on-date",
        headers=auth_header(token),
        params={"date": "2026-01-10"},
    )
    assert expired_slice.status_code == 200
    jan_codes = {item["product_code"] for item in expired_slice.json()["data"]}
    assert TEST_PRODUCT_C in jan_codes
    assert TEST_PRODUCT_B not in jan_codes

    await delete_request(seeded["request_id"])
    await delete_request(seeded["expired_request_id"])
    await delete_request(seeded["future_request_id"])
    await _cleanup_products([TEST_PRODUCT_A, TEST_PRODUCT_B, TEST_PRODUCT_C])


async def test_calculate_normative_formula(
    client: AsyncClient, test_user: AuthUser, catalog: dict[str, int]
) -> None:
    seeded = await _seed_normatives(catalog, test_user)
    token = await login_token(client, test_user)
    response = await client.get(
        "/api/v1/normatives/calculate",
        headers=auth_header(token),
        params={
            "product_code": TEST_PRODUCT_A,
            "warehouse_code": catalog["warehouse_code"],
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["product_code"] == TEST_PRODUCT_A
    assert data["warehouse_code"] == catalog["warehouse_code"]
    assert data["monthly_consumption"] == 1000
    assert data["distance_factor"] == 1
    assert data["category_factor"] == 1
    assert data["calculated_normative"] == 1000

    category_b = await client.get(
        "/api/v1/normatives/calculate",
        headers=auth_header(token),
        params={
            "product_code": TEST_PRODUCT_B,
            "warehouse_code": catalog["warehouse_code"],
        },
    )
    assert category_b.status_code == 200
    assert category_b.json()["data"]["category_factor"] == 1.5
    assert category_b.json()["data"]["calculated_normative"] == 750

    category_c = await client.get(
        "/api/v1/normatives/calculate",
        headers=auth_header(token),
        params={
            "product_code": TEST_PRODUCT_C,
            "warehouse_code": catalog["warehouse_code"],
        },
    )
    assert category_c.status_code == 200
    assert category_c.json()["data"]["category_factor"] == 2
    assert category_c.json()["data"]["calculated_normative"] == 240

    missing = await client.get(
        "/api/v1/normatives/calculate",
        headers=auth_header(token),
        params={"product_code": 999999, "warehouse_code": catalog["warehouse_code"]},
    )
    assert missing.status_code == 404

    await delete_request(seeded["request_id"])
    await delete_request(seeded["expired_request_id"])
    await delete_request(seeded["future_request_id"])
    await _cleanup_products([TEST_PRODUCT_A, TEST_PRODUCT_B, TEST_PRODUCT_C])


async def test_normatives_require_auth(client: AsyncClient) -> None:
    response = await client.get("/api/v1/normatives")
    assert response.status_code == 401
