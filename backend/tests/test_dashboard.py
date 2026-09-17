from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import delete, select

from app.core.database import AsyncSessionLocal
from app.models.available_balance import AvailableBalance
from app.models.normative import Normative
from app.models.product import Product
from app.models.production_request import ProductionRequest, ProductionRequestItem
from app.models.request import Request
from tests.conftest import AuthUser, auth_header, delete_request, login_token

TEST_PRODUCT_DEFICIT = 29001
TEST_PRODUCT_OK = 29002
CLIENT_NAME = "Тест дашборда LOG-024"


@pytest.fixture
async def dashboard_catalog(catalog: dict[str, int], test_user: AuthUser):
    request_id = uuid4()
    warehouse_code = catalog["warehouse_code"]
    product_codes = [TEST_PRODUCT_DEFICIT, TEST_PRODUCT_OK]
    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(AvailableBalance).where(
                AvailableBalance.product_code.in_(product_codes)
            )
        )
        await session.execute(
            delete(Normative).where(Normative.product_code.in_(product_codes))
        )
        leftover_ids = (
            await session.scalars(
                select(Request.id).where(Request.client_name == CLIENT_NAME)
            )
        ).all()
        if leftover_ids:
            await session.execute(delete(Request).where(Request.id.in_(leftover_ids)))
        await session.execute(delete(Product).where(Product.code.in_(product_codes)))
        await session.commit()

    async with AsyncSessionLocal() as session:
        for product in (
            Product(
                code=TEST_PRODUCT_DEFICIT,
                name="Дашборд дефицит",
                category="A",
                plant_id=catalog["plant_code"],
                weight_kg=Decimal("0.2500"),
                is_active=True,
            ),
            Product(
                code=TEST_PRODUCT_OK,
                name="Дашборд без дефицита",
                category="A",
                plant_id=catalog["plant_code"],
                weight_kg=Decimal("2.5000"),
                is_active=True,
            ),
        ):
            session.add(product)
        session.add(
            Request(
                id=request_id,
                request_type="normative",
                status="active",
                client_name=CLIENT_NAME,
                initiator_id=test_user.id,
                expiry_date=date(2026, 12, 31),
            )
        )
        session.add(
            Normative(
                request_id=request_id,
                product_code=TEST_PRODUCT_DEFICIT,
                warehouse_code=warehouse_code,
                quantity=Decimal("1000"),
                unit="шт",
                client_name=CLIENT_NAME,
                expiry_date=date(2026, 12, 31),
                category="A",
            )
        )
        session.add(
            Normative(
                request_id=request_id,
                product_code=TEST_PRODUCT_OK,
                warehouse_code=warehouse_code,
                quantity=Decimal("500"),
                unit="шт",
                client_name=CLIENT_NAME,
                expiry_date=date(2026, 12, 31),
                category="A",
            )
        )
        session.add(
            AvailableBalance(
                warehouse_code=warehouse_code,
                product_code=TEST_PRODUCT_DEFICIT,
                available=Decimal("600"),
                plan=Decimal("600"),
                unit="шт",
                source="manual",
            )
        )
        session.add(
            AvailableBalance(
                warehouse_code=warehouse_code,
                product_code=TEST_PRODUCT_OK,
                available=Decimal("500"),
                plan=Decimal("500"),
                unit="шт",
                source="manual",
            )
        )
        await session.commit()

    yield {
        "request_id": request_id,
        "warehouse_code": warehouse_code,
        "plant_code": catalog["plant_code"],
    }

    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(AvailableBalance).where(
                AvailableBalance.product_code.in_(product_codes)
            )
        )
        await session.commit()
    await delete_request(request_id)
    async with AsyncSessionLocal() as session:
        await session.execute(delete(Product).where(Product.code.in_(product_codes)))
        await session.commit()


@pytest.mark.asyncio
async def test_dashboard_requires_auth(client: AsyncClient) -> None:
    response = await client.get("/api/v1/dashboard/summary")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_dashboard_summary_metrics(
    client: AsyncClient,
    logistics_user: AuthUser,
    dashboard_catalog: dict,
) -> None:
    token = await login_token(client, logistics_user)
    response = await client.get(
        "/api/v1/dashboard/summary", headers=auth_header(token)
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["unit"] == "т"
    assert data["active_count"] >= 2
    assert Decimal(str(data["deficit_quantity"])) >= Decimal("0.1")
    assert data["coverage_pct"] <= 100
    assert data["expiring_30d"] >= 0

    kg_response = await client.get(
        "/api/v1/dashboard/summary",
        headers=auth_header(token),
        params={"unit": "кг"},
    )
    assert kg_response.status_code == 200, kg_response.text
    kg_data = kg_response.json()["data"]
    assert kg_data["unit"] == "кг"
    assert Decimal(str(kg_data["deficit_quantity"])) >= Decimal("100")


@pytest.mark.asyncio
async def test_dashboard_normative_trend_series_and_filters(
    client: AsyncClient,
    logistics_user: AuthUser,
    dashboard_catalog: dict,
) -> None:
    token = await login_token(client, logistics_user)
    today = date.today().isoformat()
    response = await client.get(
        "/api/v1/dashboard/normative-trend",
        headers=auth_header(token),
        params={
            "group_by": "day",
            "date_from": today,
            "date_to": today,
            "warehouse_code": dashboard_catalog["warehouse_code"],
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()["data"]
    assert payload["unit"] == "т"
    assert payload["group_by"] == "day"
    assert payload["periods"] == [today]
    assert len(payload["series"]) <= 10
    if len(payload["series"]) == 10:
        assert payload["series"][-1]["product_name"] == "Остальные"

    filtered = await client.get(
        "/api/v1/dashboard/normative-trend",
        headers=auth_header(token),
        params={
            "period": "day",
            "date_from": today,
            "date_to": today,
            "product_code": TEST_PRODUCT_DEFICIT,
        },
    )
    assert filtered.status_code == 200, filtered.text
    series = filtered.json()["data"]["series"]
    assert len(series) == 1
    assert series[0]["warehouse_code"] == dashboard_catalog["warehouse_code"]
    assert Decimal(str(series[0]["points"][0]["total_normative"])) == Decimal("0.25")


@pytest.mark.asyncio
async def test_dashboard_exceptions_only_deficit(
    client: AsyncClient,
    logistics_user: AuthUser,
    dashboard_catalog: dict,
) -> None:
    token = await login_token(client, logistics_user)
    response = await client.get(
        "/api/v1/dashboard/exceptions",
        headers=auth_header(token),
        params={
            "warehouse_code": dashboard_catalog["warehouse_code"],
            "limit": 200,
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    codes = {item["product_code"] for item in body["data"]}
    assert TEST_PRODUCT_DEFICIT in codes
    assert TEST_PRODUCT_OK not in codes
    assert all(item["deficit"] > 0 for item in body["data"])
    item = next(
        row for row in body["data"] if row["product_code"] == TEST_PRODUCT_DEFICIT
    )
    assert item["status"] == "critical"
    assert item["unit"] == "т"
    assert item["request_id"] == str(dashboard_catalog["request_id"])
    assert body["meta"]["total"] >= 1


@pytest.mark.asyncio
async def test_dashboard_expiry_calendar(
    client: AsyncClient,
    logistics_user: AuthUser,
    dashboard_catalog: dict,
) -> None:
    token = await login_token(client, logistics_user)
    soon = date.today() + timedelta(days=5)
    async with AsyncSessionLocal() as session:
        normative = await session.scalar(
            select(Normative).where(Normative.product_code == TEST_PRODUCT_OK)
        )
        assert normative is not None
        normative.expiry_date = soon
        await session.commit()

    response = await client.get(
        "/api/v1/dashboard/expiry-calendar",
        headers=auth_header(token),
        params={
            "date_from": date.today().isoformat(),
            "date_to": (date.today() + timedelta(days=10)).isoformat(),
        },
    )
    assert response.status_code == 200, response.text
    days = {item["date"]: item for item in response.json()["data"]["days"]}
    assert soon.isoformat() in days
    assert days[soon.isoformat()]["count"] == 1
    assert Decimal(str(days[soon.isoformat()]["quantity"])) == Decimal("1.25")


@pytest.mark.asyncio
async def test_dashboard_trend_spans_validity_window(
    client: AsyncClient,
    logistics_user: AuthUser,
    dashboard_catalog: dict,
) -> None:
    token = await login_token(client, logistics_user)
    started = date.today() - timedelta(days=4)
    until = date.today() + timedelta(days=3)
    async with AsyncSessionLocal() as session:
        normative = await session.scalar(
            select(Normative).where(Normative.product_code == TEST_PRODUCT_DEFICIT)
        )
        assert normative is not None
        normative.created_at = datetime(
            started.year, started.month, started.day, tzinfo=UTC
        )
        normative.expiry_date = until
        await session.commit()

    response = await client.get(
        "/api/v1/dashboard/normative-trend",
        headers=auth_header(token),
        params={
            "group_by": "day",
            "date_from": started.isoformat(),
            "date_to": until.isoformat(),
            "product_code": TEST_PRODUCT_DEFICIT,
        },
    )
    assert response.status_code == 200, response.text
    points = response.json()["data"]["series"][0]["points"]
    assert len(points) == (until - started).days + 1
    assert all(item["count_active"] == 1 for item in points)
    assert all(
        Decimal(str(item["total_normative"])) == Decimal("0.25") for item in points
    )


@pytest.mark.asyncio
async def test_dashboard_trend_includes_excel_production_batches(
    client: AsyncClient,
    logistics_user: AuthUser,
    dashboard_catalog: dict,
) -> None:
    token = await login_token(client, logistics_user)
    product_code = 29003
    valid_from = date.today() + timedelta(days=7)
    valid_to = date.today() + timedelta(days=14)
    batch_id = uuid4()
    item_id = uuid4()
    async with AsyncSessionLocal() as session:
        session.add(
            Product(
                code=product_code,
                name="Дашборд партия Excel",
                category="A",
                plant_id=dashboard_catalog["plant_code"],
                weight_kg=Decimal("1.0000"),
                is_active=True,
            )
        )
        session.add(
            ProductionRequest(
                id=batch_id,
                uploaded_by=logistics_user.id,
                client_name="Партия дашборда",
                valid_from=valid_from,
                valid_to=valid_to,
                status="active",
                source="excel_upload",
            )
        )
        session.add(
            ProductionRequestItem(
                id=item_id,
                production_request_id=batch_id,
                product_code=product_code,
                warehouse_code=dashboard_catalog["warehouse_code"],
                quantity=Decimal("2000"),
                unit="шт",
                client_name="Партия дашборда",
                category="A",
            )
        )
        session.add(
            Normative(
                production_request_item_id=item_id,
                product_code=product_code,
                warehouse_code=dashboard_catalog["warehouse_code"],
                quantity=Decimal("2000"),
                unit="шт",
                client_name="Партия дашборда",
                expiry_date=valid_to,
                category="A",
                created_at=datetime.now(UTC) - timedelta(days=30),
            )
        )
        await session.commit()

    try:
        response = await client.get(
            "/api/v1/dashboard/normative-trend",
            headers=auth_header(token),
            params={
                "group_by": "day",
                "date_from": date.today().isoformat(),
                "date_to": valid_to.isoformat(),
                "product_code": product_code,
                "unit": "т",
            },
        )
        assert response.status_code == 200, response.text
        points = {
            item["period"]: item
            for item in response.json()["data"]["series"][0]["points"]
        }
        assert points[date.today().isoformat()]["count_active"] == 0
        assert points[valid_from.isoformat()]["count_active"] == 1
        mass = Decimal(str(points[valid_from.isoformat()]["total_normative"]))
        assert mass == Decimal("2")
        assert points[valid_to.isoformat()]["count_active"] == 1

        kg_response = await client.get(
            "/api/v1/dashboard/normative-trend",
            headers=auth_header(token),
            params={
                "group_by": "day",
                "date_from": valid_from.isoformat(),
                "date_to": valid_from.isoformat(),
                "product_code": product_code,
                "unit": "кг",
            },
        )
        assert kg_response.status_code == 200, kg_response.text
        kg_point = kg_response.json()["data"]["series"][0]["points"][0]
        assert kg_response.json()["data"]["unit"] == "кг"
        assert Decimal(str(kg_point["total_normative"])) == Decimal("2000")
    finally:
        async with AsyncSessionLocal() as session:
            await session.execute(
                delete(Normative).where(Normative.product_code == product_code)
            )
            await session.execute(
                delete(ProductionRequestItem).where(
                    ProductionRequestItem.id == item_id
                )
            )
            await session.execute(
                delete(ProductionRequest).where(ProductionRequest.id == batch_id)
            )
            await session.execute(delete(Product).where(Product.code == product_code))
            await session.commit()


def test_collapse_top_skus_groups_remainder() -> None:
    from app.schemas.dashboard import TrendPoint, TrendSeries
    from app.services.dashboard import OTHERS_LABEL, _collapse_top_skus

    period = date.today()
    series = [
        TrendSeries(
            key=f"product:{index}",
            warehouse_code=1,
            warehouse_name="Склад",
            product_code=index,
            product_name=f"SKU {index}",
            points=[
                TrendPoint(
                    period=period,
                    total_normative=Decimal(index),
                    count_active=1,
                )
            ],
        )
        for index in range(1, 13)
    ]
    collapsed = _collapse_top_skus(series, [period], "т")
    assert len(collapsed) == 10
    assert collapsed[-1].product_name == OTHERS_LABEL
    assert Decimal(str(collapsed[-1].points[0].total_normative)) == Decimal("6")


@pytest.mark.asyncio
async def test_dashboard_warehouse_coverage_and_exceptions_limit(
    client: AsyncClient,
    logistics_user: AuthUser,
    dashboard_catalog: dict,
) -> None:
    token = await login_token(client, logistics_user)
    coverage = await client.get(
        "/api/v1/dashboard/warehouse-coverage",
        headers=auth_header(token),
    )
    assert coverage.status_code == 200, coverage.text
    warehouses = coverage.json()["data"]["warehouses"]
    match = next(
        item
        for item in warehouses
        if item["warehouse_code"] == dashboard_catalog["warehouse_code"]
    )
    assert Decimal(str(match["normative_quantity"])) > 0
    assert "available" in match
    assert "planned" in match
    assert Decimal(str(match["planned"])) >= 0
    assert "deficit" in match
    assert match["unit"] == "т"

    exceptions = await client.get(
        "/api/v1/dashboard/exceptions",
        headers=auth_header(token),
        params={"warehouse_code": dashboard_catalog["warehouse_code"]},
    )
    assert exceptions.status_code == 200, exceptions.text
    body = exceptions.json()
    assert body["meta"]["limit"] == 20
    deficits = [Decimal(str(item["deficit"])) for item in body["data"]]
    assert deficits == sorted(deficits, reverse=True)
