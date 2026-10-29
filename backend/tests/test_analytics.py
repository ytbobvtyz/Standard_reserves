from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import delete, select

from app.core.database import AsyncSessionLocal
from app.models.actual_shipment import ActualShipment
from app.models.available_balance_history import AvailableBalanceHistory
from app.models.client import Client
from app.models.department import Department
from app.models.normative import Normative
from app.models.object import Object
from app.models.product import Product
from app.models.production_request import ProductionRequest, ProductionRequestItem
from app.services.analytics import get_stock_summary
from tests.conftest import AuthUser, auth_header, login_token

PRODUCT = 29054
OTHER_PRODUCT = 29055
WAREHOUSE = 29054
OTHER_WAREHOUSE = 29055
DAY_FROM = "2026-10-01"
DAY_TO = "2026-10-06"


def _tons(values: list[object]) -> list[Decimal | None]:
    parsed: list[Decimal | None] = []
    for value in values:
        if value is None:
            parsed.append(None)
            continue
        parsed.append(Decimal(str(value)).quantize(Decimal("0.001")))
    return parsed


async def _purge() -> None:
    product_codes = [PRODUCT, OTHER_PRODUCT]
    warehouse_codes = [WAREHOUSE, OTHER_WAREHOUSE]
    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(ActualShipment).where(ActualShipment.product_code.in_(product_codes))
        )
        await session.execute(
            delete(AvailableBalanceHistory).where(
                AvailableBalanceHistory.product_code.in_(product_codes)
            )
        )
        await session.execute(
            delete(Normative).where(Normative.product_code.in_(product_codes))
        )
        request_ids = (
            await session.scalars(
                select(ProductionRequestItem.production_request_id).where(
                    ProductionRequestItem.product_code.in_(product_codes)
                )
            )
        ).all()
        await session.execute(
            delete(ProductionRequestItem).where(
                ProductionRequestItem.product_code.in_(product_codes)
            )
        )
        if request_ids:
            await session.execute(
                delete(ProductionRequest).where(ProductionRequest.id.in_(request_ids))
            )
        await session.execute(delete(Product).where(Product.code.in_(product_codes)))
        await session.execute(delete(Object).where(Object.code.in_(warehouse_codes)))
        await session.commit()


@pytest.fixture
async def stock_dataset(catalog: dict[str, int], logistics_user: AuthUser):
    await _purge()
    department_a = uuid4()
    department_b = uuid4()
    client_a = uuid4()
    client_b = uuid4()
    suffix = uuid4().hex[:8]
    created = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
    created_later = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)
    async with AsyncSessionLocal() as session:
        session.add_all(
            [
                Department(
                    id=department_a,
                    name=f"Аналитика А {suffix}",
                    is_active=True,
                ),
                Department(
                    id=department_b,
                    name=f"Аналитика Б {suffix}",
                    is_active=True,
                ),
            ]
        )
        await session.flush()
        session.add_all(
            [
                Client(
                    id=client_a,
                    client_code=8_100_000_000 + int(suffix[:4], 16),
                    inn=f"{int(suffix[:6], 16):010d}"[-10:],
                    name=f"Клиент А {suffix}",
                    department_id=department_a,
                    is_active=True,
                    is_system=False,
                ),
                Client(
                    id=client_b,
                    client_code=8_200_000_000 + int(suffix[4:], 16),
                    inn=f"{int(suffix, 16):010d}"[-10:],
                    name=f"Клиент Б {suffix}",
                    department_id=department_b,
                    is_active=True,
                    is_system=False,
                ),
            ]
        )
        session.add_all(
            [
                Object(
                    code=WAREHOUSE,
                    name="Склад аналитики 1",
                    city="Тула",
                    type="warehouse",
                    loading_point="T954",
                    is_active=True,
                ),
                Object(
                    code=OTHER_WAREHOUSE,
                    name="Склад аналитики 2",
                    city="Тула",
                    type="warehouse",
                    loading_point="T955",
                    is_active=True,
                ),
                Product(
                    code=PRODUCT,
                    name="Продукт аналитики",
                    category="A",
                    plant_id=catalog["plant_code"],
                    weight_kg=Decimal("1.0000"),
                    is_active=True,
                ),
                Product(
                    code=OTHER_PRODUCT,
                    name="Чужой продукт аналитики",
                    category="A",
                    plant_id=catalog["plant_code"],
                    weight_kg=Decimal("1.0000"),
                    is_active=True,
                ),
            ]
        )
        await session.flush()
        active_batch = ProductionRequest(
            uploaded_by=logistics_user.id,
            valid_from=date(2026, 10, 15),
            valid_to=date(2026, 10, 25),
            status="active",
            client_name="Клиент А",
        )
        cancelled_batch = ProductionRequest(
            uploaded_by=logistics_user.id,
            valid_from=date(2026, 10, 1),
            valid_to=date(2026, 10, 25),
            status="cancelled",
            client_name="Клиент А",
        )
        session.add_all([active_batch, cancelled_batch])
        await session.flush()
        active_item = ProductionRequestItem(
            production_request_id=active_batch.id,
            product_code=PRODUCT,
            warehouse_code=WAREHOUSE,
            quantity=Decimal("2"),
            unit="т",
            client_name="Клиент А",
            category="A",
        )
        cancelled_item = ProductionRequestItem(
            production_request_id=cancelled_batch.id,
            product_code=PRODUCT,
            warehouse_code=WAREHOUSE,
            quantity=Decimal("1000"),
            unit="т",
            client_name="Клиент А",
            category="A",
        )
        session.add_all([active_item, cancelled_item])
        await session.flush()
        session.add_all(
            [
                Normative(
                    product_code=PRODUCT,
                    warehouse_code=WAREHOUSE,
                    quantity=Decimal("10"),
                    unit="т",
                    client_name="Клиент А",
                    client_id=client_a,
                    expiry_date=date(2026, 10, 20),
                    category="A",
                    created_at=created,
                ),
                Normative(
                    product_code=PRODUCT,
                    warehouse_code=WAREHOUSE,
                    quantity=Decimal("5"),
                    unit="т",
                    client_name="Клиент Б",
                    client_id=client_b,
                    expiry_date=date(2026, 10, 10),
                    category="A",
                    created_at=created,
                ),
                Normative(
                    product_code=PRODUCT,
                    warehouse_code=OTHER_WAREHOUSE,
                    quantity=Decimal("3"),
                    unit="т",
                    client_name="Клиент А",
                    client_id=client_a,
                    expiry_date=date(2026, 10, 20),
                    category="A",
                    created_at=created_later,
                ),
                Normative(
                    product_code=PRODUCT,
                    warehouse_code=WAREHOUSE,
                    quantity=Decimal("100"),
                    unit="т",
                    client_name="Клиент А",
                    client_id=client_a,
                    expiry_date=date(2026, 10, 20),
                    category="A",
                    created_at=created,
                    deleted_at=datetime(2026, 10, 2, tzinfo=UTC),
                ),
                Normative(
                    product_code=OTHER_PRODUCT,
                    warehouse_code=WAREHOUSE,
                    quantity=Decimal("99"),
                    unit="т",
                    client_name="Клиент А",
                    client_id=client_a,
                    expiry_date=date(2026, 10, 20),
                    category="A",
                    created_at=created,
                ),
                Normative(
                    production_request_item_id=active_item.id,
                    product_code=PRODUCT,
                    warehouse_code=WAREHOUSE,
                    quantity=Decimal("2"),
                    unit="т",
                    client_name="Клиент А",
                    client_id=client_a,
                    expiry_date=date(2026, 10, 25),
                    category="A",
                    created_at=created,
                ),
                Normative(
                    production_request_item_id=cancelled_item.id,
                    product_code=PRODUCT,
                    warehouse_code=WAREHOUSE,
                    quantity=Decimal("1000"),
                    unit="т",
                    client_name="Клиент А",
                    client_id=client_a,
                    expiry_date=date(2026, 10, 25),
                    category="A",
                    created_at=created,
                ),
                Normative(
                    product_code=PRODUCT,
                    warehouse_code=WAREHOUSE,
                    quantity=Decimal("1.2345"),
                    unit="т",
                    client_name="Клиент А",
                    client_id=client_a,
                    expiry_date=date(2026, 10, 26),
                    category="A",
                    created_at=datetime(2026, 10, 26, 12, 0, tzinfo=UTC),
                ),
            ]
        )
        session.add_all(
            [
                AvailableBalanceHistory(
                    snapshot_date=date(2026, 10, 2),
                    snapshot_at=datetime(2026, 10, 2, 12, tzinfo=UTC),
                    warehouse_code=WAREHOUSE,
                    product_code=PRODUCT,
                    available=Decimal("8"),
                    plan=Decimal("8"),
                    unit="т",
                ),
                AvailableBalanceHistory(
                    snapshot_date=date(2026, 10, 3),
                    snapshot_at=datetime(2026, 10, 3, 12, tzinfo=UTC),
                    warehouse_code=WAREHOUSE,
                    product_code=PRODUCT,
                    available=Decimal("-5"),
                    plan=Decimal("-5"),
                    unit="т",
                ),
                AvailableBalanceHistory(
                    snapshot_date=date(2026, 10, 4),
                    snapshot_at=datetime(2026, 10, 4, 8, tzinfo=UTC),
                    warehouse_code=WAREHOUSE,
                    product_code=PRODUCT,
                    available=Decimal("9"),
                    plan=Decimal("9"),
                    unit="т",
                ),
                AvailableBalanceHistory(
                    snapshot_date=date(2026, 10, 4),
                    snapshot_at=datetime(2026, 10, 4, 8, tzinfo=UTC),
                    warehouse_code=OTHER_WAREHOUSE,
                    product_code=PRODUCT,
                    available=Decimal("1"),
                    plan=Decimal("1"),
                    unit="т",
                ),
                AvailableBalanceHistory(
                    snapshot_date=date(2026, 10, 16),
                    snapshot_at=datetime(2026, 10, 16, 12, tzinfo=UTC),
                    warehouse_code=WAREHOUSE,
                    product_code=PRODUCT,
                    available=Decimal("4"),
                    plan=Decimal("4"),
                    unit="т",
                ),
                AvailableBalanceHistory(
                    snapshot_date=date(2026, 10, 2),
                    snapshot_at=datetime(2026, 10, 2, 12, tzinfo=UTC),
                    warehouse_code=WAREHOUSE,
                    product_code=OTHER_PRODUCT,
                    available=Decimal("50"),
                    plan=Decimal("50"),
                    unit="т",
                ),
            ]
        )
        session.add_all(
            [
                ActualShipment(
                    client_id=client_a,
                    product_code=PRODUCT,
                    quantity=Decimal("1500"),
                    unit="кг",
                    shipment_date=date(2026, 10, 3),
                    loading_point="T954",
                ),
                ActualShipment(
                    client_id=client_a,
                    product_code=PRODUCT,
                    quantity=Decimal("0.5"),
                    unit="т",
                    shipment_date=date(2026, 10, 4),
                    loading_point="T954",
                ),
                ActualShipment(
                    client_id=client_b,
                    product_code=PRODUCT,
                    quantity=Decimal("2"),
                    unit="т",
                    shipment_date=date(2026, 10, 6),
                    loading_point="T954",
                ),
                ActualShipment(
                    client_id=client_a,
                    product_code=PRODUCT,
                    quantity=Decimal("1"),
                    unit="т",
                    shipment_date=date(2026, 10, 8),
                    loading_point="T955",
                ),
                ActualShipment(
                    client_id=client_a,
                    product_code=PRODUCT,
                    quantity=Decimal("3"),
                    unit="т",
                    shipment_date=date(2026, 10, 16),
                    loading_point="T954",
                ),
                ActualShipment(
                    client_id=client_a,
                    product_code=PRODUCT,
                    quantity=Decimal("9"),
                    unit="т",
                    shipment_date=date(2026, 10, 3),
                    loading_point="T954",
                    deleted_at=datetime(2026, 10, 3, tzinfo=UTC),
                ),
                ActualShipment(
                    client_id=client_a,
                    product_code=OTHER_PRODUCT,
                    quantity=Decimal("7"),
                    unit="т",
                    shipment_date=date(2026, 10, 3),
                    loading_point="T954",
                ),
            ]
        )
        await session.commit()
    payload = {
        "client_a": str(client_a),
        "client_b": str(client_b),
        "department_a": str(department_a),
        "department_b": str(department_b),
    }
    yield payload
    await _purge()
    async with AsyncSessionLocal() as session:
        await session.execute(delete(Client).where(Client.id.in_([client_a, client_b])))
        await session.execute(
            delete(Department).where(Department.id.in_([department_a, department_b]))
        )
        await session.commit()


async def _get(
    client: AsyncClient,
    token: str,
    params: dict,
    path: str = "/api/v1/analytics/stock-dynamics",
):
    response = await client.get(path, headers=auth_header(token), params=params)
    assert response.status_code == 200, response.text
    return response.json()["data"]


@pytest.mark.asyncio
async def test_stock_dynamics_requires_auth(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/analytics/stock-dynamics",
        params={"product_code": PRODUCT, "date_from": DAY_FROM, "date_to": DAY_TO},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_stock_dynamics_guest_can_read(
    client: AsyncClient,
    guest_user: AuthUser,
    stock_dataset: dict,
) -> None:
    token = await login_token(client, guest_user)
    data = await _get(
        client,
        token,
        {"product_code": PRODUCT, "date_from": DAY_FROM, "date_to": DAY_TO},
    )
    assert data["unit"] == "т"
    assert data["dates"][0] == DAY_FROM


@pytest.mark.asyncio
async def test_stock_dynamics_rejects_inverted_period(
    client: AsyncClient,
    guest_user: AuthUser,
) -> None:
    token = await login_token(client, guest_user)
    response = await client.get(
        "/api/v1/analytics/stock-dynamics",
        headers=auth_header(token),
        params={"product_code": PRODUCT, "date_from": DAY_TO, "date_to": DAY_FROM},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_stock_dynamics_day_sums_filters_and_nulls(
    client: AsyncClient,
    logistics_user: AuthUser,
    stock_dataset: dict,
) -> None:
    token = await login_token(client, logistics_user)
    day = {"granularity": "day", "date_from": DAY_FROM, "date_to": DAY_TO}
    data = await _get(client, token, {"product_code": PRODUCT, **day})
    assert data["dates"] == [
        "2026-10-01",
        "2026-10-02",
        "2026-10-03",
        "2026-10-04",
        "2026-10-05",
        "2026-10-06",
    ]
    assert _tons(data["normative"]) == [
        Decimal("0.536"),
        Decimal("0.536"),
        Decimal("0.536"),
        Decimal("0.536"),
        Decimal("0.643"),
        Decimal("0.643"),
    ]
    assert data["available_min"] == [None] * 6
    assert _tons(data["available_median"]) == [
        None,
        Decimal("8.000"),
        Decimal("0.000"),
        Decimal("10.000"),
        None,
        None,
    ]
    assert data["available_max"] == [None] * 6
    assert _tons(data["actual"]) == [
        None,
        None,
        Decimal("1.500"),
        Decimal("0.500"),
        None,
        Decimal("2.000"),
    ]

    client_only = await _get(
        client,
        token,
        {"product_code": PRODUCT, "client_id": stock_dataset["client_a"], **day},
    )
    assert _tons(client_only["normative"]) == [
        Decimal("0.357"),
        Decimal("0.357"),
        Decimal("0.357"),
        Decimal("0.357"),
        Decimal("0.464"),
        Decimal("0.464"),
    ]
    assert _tons(client_only["available_median"]) == _tons(data["available_median"])
    assert _tons(client_only["actual"]) == [
        None,
        None,
        Decimal("1.500"),
        Decimal("0.500"),
        None,
        None,
    ]

    department = await _get(
        client,
        token,
        {
            "product_code": PRODUCT,
            "department_id": stock_dataset["department_a"],
            **day,
        },
    )
    assert _tons(department["normative"]) == _tons(client_only["normative"])
    assert _tons(department["actual"]) == _tons(client_only["actual"])

    warehouse = await _get(
        client,
        token,
        {"product_code": PRODUCT, "warehouse_code": WAREHOUSE, **day},
    )
    assert _tons(warehouse["normative"]) == [Decimal("0.536")] * 6
    assert warehouse["available_min"] == [None] * 6
    assert _tons(warehouse["available_median"]) == [
        None,
        Decimal("8.000"),
        Decimal("0.000"),
        Decimal("9.000"),
        None,
        None,
    ]
    assert warehouse["available_max"] == [None] * 6


@pytest.mark.asyncio
async def test_stock_dynamics_week_month_and_rounding(
    client: AsyncClient,
    logistics_user: AuthUser,
    stock_dataset: dict,
) -> None:
    token = await login_token(client, logistics_user)
    week = await _get(
        client,
        token,
        {
            "product_code": PRODUCT,
            "date_from": "2026-10-05",
            "date_to": "2026-10-20",
            "granularity": "week",
        },
    )
    assert week["dates"] == ["2026-10-05", "2026-10-12", "2026-10-19"]
    assert _tons(week["normative"]) == [
        Decimal("4.500"),
        Decimal("3.750"),
        Decimal("3.750"),
    ]
    assert _tons(week["available_min"]) == [None, Decimal("4.000"), None]
    assert week["available_median"] == [None, None, None]
    assert _tons(week["available_max"]) == [None, Decimal("4.000"), None]

    week_span = await _get(
        client,
        token,
        {
            "product_code": PRODUCT,
            "date_from": "2026-10-01",
            "date_to": "2026-10-11",
            "granularity": "week",
        },
    )
    assert week_span["dates"] == ["2026-09-28", "2026-10-05"]
    assert _tons(week_span["available_min"]) == [Decimal("0.000"), None]
    assert week_span["available_median"] == [None, None]
    assert _tons(week_span["available_max"]) == [Decimal("10.000"), None]
    assert _tons(week["actual"]) == [
        Decimal("3.000"),
        Decimal("3.000"),
        None,
    ]

    month = await _get(
        client,
        token,
        {
            "product_code": PRODUCT,
            "date_from": "2026-10-01",
            "date_to": "2026-10-31",
            "granularity": "month",
        },
    )
    assert month["dates"] == ["2026-10-01"]
    assert _tons(month["normative"]) == [Decimal("21.235")]
    assert _tons(month["available_min"]) == [Decimal("0.000")]
    assert _tons(month["available_median"]) == [Decimal("6.000")]
    assert _tons(month["available_max"]) == [Decimal("10.000")]
    assert _tons(month["actual"]) == [Decimal("8.000")]

    rounded = await _get(
        client,
        token,
        {
            "product_code": PRODUCT,
            "date_from": "2026-10-26",
            "date_to": "2026-10-26",
            "granularity": "day",
        },
    )
    assert _tons(rounded["normative"]) == [Decimal("0.044")]
    assert rounded["available_median"] == [None]
    assert rounded["actual"] == [None]


@pytest.mark.asyncio
async def test_stock_dynamics_bounds_follow_filters(
    client: AsyncClient,
    logistics_user: AuthUser,
    stock_dataset: dict,
) -> None:
    token = await login_token(client, logistics_user)
    bounds = await _get(
        client,
        token,
        {"product_code": PRODUCT},
        "/api/v1/analytics/stock-dynamics/bounds",
    )
    assert bounds["earliest_date"] == "2026-10-01"

    warehouse = await _get(
        client,
        token,
        {"product_code": PRODUCT, "warehouse_code": OTHER_WAREHOUSE},
        "/api/v1/analytics/stock-dynamics/bounds",
    )
    assert warehouse["earliest_date"] == "2026-10-04"

    unknown_client = await _get(
        client,
        token,
        {"product_code": PRODUCT, "client_id": str(uuid4())},
        "/api/v1/analytics/stock-dynamics/bounds",
    )
    assert unknown_client["earliest_date"] == "2026-10-02"

    empty = await _get(
        client,
        token,
        {
            "product_code": PRODUCT,
            "date_from": "2026-09-01",
            "date_to": "2026-09-02",
            "granularity": "day",
        },
    )
    assert empty["normative"] == [None, None]
    assert empty["available_min"] == [None, None]
    assert empty["available_median"] == [None, None]
    assert empty["available_max"] == [None, None]
    assert empty["actual"] == [None, None]


@pytest.mark.asyncio
async def test_stock_summary_last_three_months(
    client: AsyncClient,
    guest_user: AuthUser,
    stock_dataset: dict,
) -> None:
    today = date(2026, 10, 6)
    async with AsyncSessionLocal() as session:
        summary = await get_stock_summary(
            session,
            product_code=PRODUCT,
            warehouse_code=None,
            department_id=None,
            client_id=None,
            today=today,
        )
    assert [item.month for item in summary.months] == [
        date(2026, 5, 1),
        date(2026, 6, 1),
        date(2026, 7, 1),
        date(2026, 8, 1),
        date(2026, 9, 1),
        date(2026, 10, 1),
    ]
    for earlier in summary.months[:-1]:
        assert earlier.normative_avg is None
        assert earlier.available_median is None
        assert earlier.actual is None
    october = summary.months[-1]
    assert october.available_median == Decimal("8.000")
    assert october.actual == Decimal("4.000")
    assert october.normative_avg == Decimal("16.000")

    async with AsyncSessionLocal() as session:
        client_only = await get_stock_summary(
            session,
            product_code=PRODUCT,
            warehouse_code=None,
            department_id=None,
            client_id=UUID(stock_dataset["client_a"]),
            today=today,
        )
    assert client_only.months[-1].available_median == Decimal("8.000")
    assert client_only.months[-1].actual == Decimal("2.000")
    assert client_only.months[-1].normative_avg == Decimal("11.000")

    token = await login_token(client, guest_user)
    response = await client.get(
        "/api/v1/analytics/stock-summary",
        headers=auth_header(token),
        params={"product_code": PRODUCT},
    )
    assert response.status_code == 200
    assert len(response.json()["data"]["months"]) == 6
