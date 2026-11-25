from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import delete

from app.core.database import AsyncSessionLocal
from app.core.exceptions import APIError
from app.models.actual_shipment import ActualShipment
from app.models.client import Client
from app.models.department import Department
from app.models.normative import Normative
from app.models.object import Object
from app.models.product import Product
from app.services.client_analytics import get_client_analytics
from tests.conftest import AuthUser, auth_header, login_token

MAIN = 39101
RELATED = 39102
WAREHOUSE = 39101
TODAY = date(2026, 11, 25)
DATE_FROM = date(2026, 6, 1)
DATE_TO = date(2026, 11, 25)


def _by_code(rows, code: int):
    return next(item for item in rows if item.code == code)


async def _purge(client_ids: list, department_id) -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(ActualShipment).where(
                ActualShipment.product_code.in_([MAIN, RELATED])
            )
        )
        await session.execute(
            delete(Normative).where(Normative.product_code.in_([MAIN, RELATED]))
        )
        await session.execute(delete(Product).where(Product.code.in_([MAIN, RELATED])))
        await session.execute(delete(Object).where(Object.code == WAREHOUSE))
        if client_ids:
            await session.execute(delete(Client).where(Client.id.in_(client_ids)))
        if department_id is not None:
            await session.execute(
                delete(Department).where(Department.id == department_id)
            )
        await session.commit()


@pytest.fixture
async def client_view(catalog: dict[str, int]):
    department_id = uuid4()
    client_id = uuid4()
    other_id = uuid4()
    suffix = uuid4().hex
    await _purge([client_id, other_id], department_id)
    async with AsyncSessionLocal() as session:
        session.add(
            Department(id=department_id, name=f"Продажи {suffix}", is_active=True)
        )
        await session.flush()
        session.add_all(
            [
                Client(
                    id=client_id,
                    client_code=7_100_000_000 + int(suffix[:6], 16) % 1_000_000,
                    inn=f"{int(suffix[:8], 16) % 10**10:010d}",
                    name=f"Клиент среза {suffix}",
                    department_id=department_id,
                    is_active=True,
                ),
                Client(
                    id=other_id,
                    client_code=7_200_000_000 + int(suffix[6:12], 16) % 1_000_000,
                    inn=f"{int(suffix[8:16], 16) % 10**10:010d}",
                    name=f"Чужой клиент {suffix}",
                    is_active=True,
                ),
                Object(
                    code=WAREHOUSE,
                    name="Склад клиента",
                    city="Тула",
                    type="warehouse",
                    loading_point="A711",
                    is_active=True,
                ),
                Product(
                    code=MAIN,
                    name="Основной артикул",
                    category="A",
                    plant_id=catalog["plant_code"],
                    weight_kg=Decimal("1"),
                    children_code=RELATED,
                    is_active=True,
                ),
                Product(
                    code=RELATED,
                    name="Родственный артикул",
                    category="A",
                    plant_id=catalog["plant_code"],
                    weight_kg=Decimal("1"),
                    parent_code=MAIN,
                    is_active=True,
                ),
            ]
        )
        session.add_all(
            [
                Normative(
                    product_code=MAIN,
                    warehouse_code=WAREHOUSE,
                    quantity=Decimal("2.4"),
                    unit="т",
                    client_name="Клиент среза",
                    client_id=client_id,
                    valid_from=date(2026, 1, 1),
                    expiry_date=date(2026, 12, 31),
                    category="A",
                    created_at=datetime(2026, 1, 1, tzinfo=UTC),
                ),
                Normative(
                    product_code=MAIN,
                    warehouse_code=WAREHOUSE,
                    quantity=Decimal("100"),
                    unit="т",
                    client_name="Клиент среза",
                    client_id=client_id,
                    valid_from=date(2026, 1, 1),
                    expiry_date=date(2026, 12, 31),
                    category="A",
                    created_at=datetime(2026, 1, 1, tzinfo=UTC),
                    deleted_at=datetime(2026, 2, 1, tzinfo=UTC),
                ),
            ]
        )
        session.add_all(
            [
                ActualShipment(
                    client_id=client_id,
                    product_code=MAIN,
                    quantity=Decimal("6000"),
                    unit="кг",
                    shipment_date=date(2026, 6, 15),
                    loading_point="A711",
                ),
                ActualShipment(
                    client_id=client_id,
                    product_code=RELATED,
                    quantity=Decimal("6000"),
                    unit="кг",
                    shipment_date=date(2026, 6, 15),
                    loading_point="A711",
                ),
                ActualShipment(
                    client_id=client_id,
                    product_code=MAIN,
                    quantity=Decimal("6000"),
                    unit="кг",
                    shipment_date=date(2026, 6, 20),
                    loading_point="Z711",
                ),
                ActualShipment(
                    client_id=client_id,
                    product_code=MAIN,
                    quantity=Decimal("9000"),
                    unit="кг",
                    shipment_date=date(2026, 11, 2),
                    loading_point="A711",
                ),
                ActualShipment(
                    client_id=other_id,
                    product_code=MAIN,
                    quantity=Decimal("50000"),
                    unit="кг",
                    shipment_date=date(2026, 6, 15),
                    loading_point="A711",
                ),
                ActualShipment(
                    client_id=client_id,
                    product_code=MAIN,
                    quantity=Decimal("50000"),
                    unit="кг",
                    shipment_date=date(2026, 6, 15),
                    loading_point="A711",
                    deleted_at=datetime(2026, 6, 16, tzinfo=UTC),
                ),
            ]
        )
        await session.commit()
    yield {"client_id": client_id, "name_prefix": suffix}
    await _purge([client_id, other_id], department_id)


async def _load(client_id, **kwargs):
    params = {
        "date_from": DATE_FROM,
        "date_to": DATE_TO,
        "granularity": "month",
        "include_related": True,
        "warehouse_codes": None,
        "product_codes": None,
        "today": TODAY,
    }
    params.update(kwargs)
    async with AsyncSessionLocal() as session:
        return await get_client_analytics(session, client_id=client_id, **params)


@pytest.mark.asyncio
async def test_client_rows_keep_consumption_without_normative(client_view) -> None:
    data = await _load(client_view["client_id"])

    assert data.department_name.startswith("Продажи")
    assert data.is_system is False
    warehouse = _by_code(data.warehouses, WAREHOUSE)
    assert warehouse.normative_tons == Decimal("2.400")
    assert warehouse.avg_monthly_tons == Decimal("2.400")
    assert warehouse.period_tons == Decimal("21.000")
    assert warehouse.coverage_months == Decimal("1.0")
    assert warehouse.outside_normative is False

    main = _by_code(data.products, MAIN)
    related = _by_code(data.products, RELATED)
    assert main.avg_monthly_tons == Decimal("2.400")
    assert main.period_tons == Decimal("21.000")
    assert main.coverage_months == Decimal("1.0")
    assert main.outside_normative is False
    assert [(item.code, item.avg_monthly_tons) for item in main.related] == [
        (RELATED, Decimal("1.200"))
    ]
    assert related.normative_tons == Decimal("0.000")
    assert related.avg_monthly_tons == Decimal("2.400")
    assert related.period_tons == Decimal("6.000")
    assert related.coverage_months == Decimal("0.0")
    assert related.outside_normative is True
    assert data.unmatched[0].loading_point == "Z711"
    assert data.unmatched[0].period_tons == Decimal("6.000")
    assert data.unmatched[0].avg_monthly_tons == Decimal("1.200")
    assert data.unmatched[0].outside_normative is True

    june = data.chart.dates.index(date(2026, 6, 1))
    november = data.chart.dates.index(date(2026, 11, 1))
    assert data.chart.normative[june] == Decimal("2.400")
    assert data.chart.actual[june] == Decimal("18.000")
    assert data.chart.actual[november] == Decimal("9.000")
    assert data.slice.normative_tons == Decimal("2.400")
    assert data.slice.avg_monthly_tons == Decimal("3.600")
    assert data.slice.coverage_months == Decimal("0.7")


@pytest.mark.asyncio
async def test_related_switch_changes_article_not_warehouse(client_view) -> None:
    client_id = client_view["client_id"]
    opened = await _load(client_id, include_related=True)
    without = await _load(client_id, include_related=False)
    main = _by_code(without.products, MAIN)
    warehouse = _by_code(without.warehouses, WAREHOUSE)
    assert main.avg_monthly_tons == Decimal("1.200")
    assert main.coverage_months == Decimal("2.0")
    assert warehouse.avg_monthly_tons == Decimal("2.400")
    assert opened.slice.avg_monthly_tons == Decimal("3.600")
    assert without.slice.avg_monthly_tons == Decimal("3.600")
    assert without.chart.actual[without.chart.dates.index(date(2026, 6, 1))] == Decimal(
        "18.000"
    )

    narrowed = await _load(
        client_id,
        include_related=True,
        product_codes=[MAIN],
        warehouse_codes=[WAREHOUSE],
    )
    june = narrowed.chart.dates.index(date(2026, 6, 1))
    assert narrowed.chart.actual[june] == Decimal("6.000")
    assert narrowed.slice.avg_monthly_tons == Decimal("2.400")
    assert narrowed.slice.normative_tons == Decimal("2.400")
    assert [row.code for row in narrowed.products] == [MAIN, RELATED]


@pytest.mark.asyncio
async def test_week_normative_uses_the_same_divisor(client_view) -> None:
    data = await _load(
        client_view["client_id"],
        date_from=date(2026, 6, 15),
        date_to=date(2026, 6, 21),
        granularity="week",
    )
    assert data.chart.dates == [date(2026, 6, 15)]
    assert data.chart.normative == [Decimal("0.600")]
    assert data.chart.actual == [Decimal("18.000")]


@pytest.mark.asyncio
async def test_empty_selection_clears_chart_and_keeps_rows(client_view) -> None:
    data = await _load(client_view["client_id"], product_codes=[])
    assert data.products
    assert data.chart.normative == [None] * len(data.chart.dates)
    assert data.chart.actual == [None] * len(data.chart.dates)
    assert data.slice.normative_tons == Decimal("0")
    assert data.slice.avg_monthly_tons is None


@pytest.mark.asyncio
async def test_unknown_client_is_not_found() -> None:
    with pytest.raises(APIError) as caught:
        await _load(uuid4())
    assert caught.value.status_code == 404


@pytest.mark.asyncio
async def test_client_analytics_route(
    client: AsyncClient,
    logistics_user: AuthUser,
    client_view,
) -> None:
    missing = await client.get(
        f"/api/v1/analytics/clients/{client_view['client_id']}",
        params={"date_from": "2026-06-01", "date_to": "2026-11-25"},
    )
    assert missing.status_code == 401

    token = await login_token(client, logistics_user)
    response = await client.get(
        f"/api/v1/analytics/clients/{client_view['client_id']}",
        params={"date_from": "2026-06-01", "date_to": "2026-11-25"},
        headers=auth_header(token),
    )
    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert any(row["outside_normative"] for row in body["products"])
    assert body["unmatched"][0]["loading_point"] == "Z711"
