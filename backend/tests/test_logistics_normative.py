from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from io import BytesIO
from uuid import uuid4

import pytest
from httpx import AsyncClient
from openpyxl import Workbook, load_workbook
from sqlalchemy import delete, select

from app.core.database import AsyncSessionLocal
from app.models.available_balance import AvailableBalance
from app.models.available_balance_history import AvailableBalanceHistory
from app.models.normative import Normative
from app.models.object import Object
from app.models.product import Product
from app.models.request import Request
from app.models.request_item import RequestItem
from app.models.sync_metadata import SyncMetadata
from app.services.coefficients import calculate_requirement
from app.services.logistics_normative import (
    LONG_DISTANCE_MESSAGE,
    _parse_int_cell,
    _parse_quantity,
    _parse_warehouse_code,
)
from tests.conftest import AuthUser, auth_header, delete_request, login_token

TEST_PRODUCT_DEFICIT = 19001
TEST_PRODUCT_OK = 19002
TEST_PRODUCT_STOCK_ONLY = 19003
CLIENT_NAME = "Тест логистика этап 5"


@pytest.fixture
async def logistics_catalog(catalog: dict[str, int], test_user: AuthUser):
    request_id = uuid4()
    warehouse_code = catalog["warehouse_code"]
    product_codes = [TEST_PRODUCT_DEFICIT, TEST_PRODUCT_OK, TEST_PRODUCT_STOCK_ONLY]
    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(AvailableBalanceHistory).where(
                AvailableBalanceHistory.product_code.in_(product_codes)
            )
        )
        await session.execute(
            delete(AvailableBalance).where(
                AvailableBalance.product_code.in_(product_codes)
            )
        )
        await session.execute(delete(SyncMetadata))
        await session.execute(
            delete(Normative).where(Normative.product_code.in_(product_codes))
        )
        leftover_ids = (
            await session.scalars(
                select(Request.id).where(Request.client_name == CLIENT_NAME)
            )
        ).all()
        await session.execute(
            delete(RequestItem).where(
                RequestItem.product_code.in_(product_codes)
                | RequestItem.request_id.in_(leftover_ids or [uuid4()])
            )
        )
        if leftover_ids:
            await session.execute(delete(Request).where(Request.id.in_(leftover_ids)))
        await session.execute(delete(Product).where(Product.code.in_(product_codes)))
        await session.commit()

    async with AsyncSessionLocal() as session:
        products = [
            Product(
                code=TEST_PRODUCT_DEFICIT,
                name="Тестовый подшипник логистики",
                category="A",
                plant_id=catalog["plant_code"],
                second_plant_id=1002,
                weight_kg=Decimal("0.2500"),
                is_active=True,
            ),
            Product(
                code=TEST_PRODUCT_OK,
                name="Тестовый корпус без дефицита",
                category="A",
                plant_id=1002,
                weight_kg=Decimal("2.5000"),
                is_active=True,
            ),
            Product(
                code=TEST_PRODUCT_STOCK_ONLY,
                name="Только фактический остаток",
                category="C",
                plant_id=catalog["plant_code"],
                weight_kg=Decimal("1.0000"),
                is_active=True,
            ),
        ]
        for product in products:
            if await session.get(Product, product.code) is None:
                session.add(product)
        await session.flush()
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
        session.add(
            AvailableBalance(
                warehouse_code=warehouse_code,
                product_code=TEST_PRODUCT_STOCK_ONLY,
                available=Decimal("80"),
                plan=Decimal("80"),
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
            delete(AvailableBalanceHistory).where(
                AvailableBalanceHistory.product_code.in_(
                    [TEST_PRODUCT_DEFICIT, TEST_PRODUCT_OK, TEST_PRODUCT_STOCK_ONLY]
                )
            )
        )
        await session.execute(
            delete(AvailableBalance).where(
                AvailableBalance.product_code.in_(
                    [TEST_PRODUCT_DEFICIT, TEST_PRODUCT_OK, TEST_PRODUCT_STOCK_ONLY]
                )
            )
        )
        await session.commit()
    await delete_request(request_id)
    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(Product).where(
                Product.code.in_(
                    [TEST_PRODUCT_DEFICIT, TEST_PRODUCT_OK, TEST_PRODUCT_STOCK_ONLY]
                )
            )
        )
        await session.commit()


def _warehouse(data: list[dict], warehouse_code: int) -> dict:
    return next(item for item in data if item["warehouse_code"] == warehouse_code)


def _item(warehouse: dict, product_code: int) -> dict:
    return next(
        item
        for item in warehouse["deficit_items"]
        if item["product_code"] == product_code
    )


async def test_dashboard_returns_deficit(
    client: AsyncClient,
    logistics_user: AuthUser,
    logistics_catalog: dict,
) -> None:
    token = await login_token(client, logistics_user)
    response = await client.get(
        "/api/v1/logistics/normative/dashboard",
        headers=auth_header(token),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "success"
    warehouse = _warehouse(body["data"], logistics_catalog["warehouse_code"])
    item = _item(warehouse, TEST_PRODUCT_DEFICIT)
    assert item["product_name"] == "Тестовый подшипник логистики"
    assert item["normative_quantity"] == 1000
    assert item["requirement"] == 1000
    assert item["available"] == 600
    assert item["no_ready"] == 0
    assert item["ready"] == 0
    assert item["collected"] == 0
    assert item["on_way"] == 0
    assert item["plan"] == 600
    assert item["plan"] == pytest.approx(
        item["available"]
        + item["no_ready"]
        + item["ready"]
        + item["collected"]
        + item["on_way"]
    )
    assert item["deficit"] == 400
    assert item["unit"] == "шт"
    assert item["status"] == "warning"
    assert item["client_name"] == CLIENT_NAME
    assert warehouse["long_distance"] is False
    assert warehouse["long_distance_message"] is None
    assert warehouse["deficit_count"] >= 1
    assert body["summary"]["deficit_products"] >= 1


async def test_dashboard_requirement_recalculates_after_coeff_change(
    client: AsyncClient,
    logistics_user: AuthUser,
    logistics_catalog: dict,
) -> None:
    warehouse_code = logistics_catalog["warehouse_code"]
    token = await login_token(client, logistics_user)
    before = await client.get(
        "/api/v1/logistics/normative/dashboard",
        params={"warehouse_code": warehouse_code},
        headers=auth_header(token),
    )
    assert before.status_code == 200, before.text
    item_before = _item(
        _warehouse(before.json()["data"], warehouse_code), TEST_PRODUCT_DEFICIT
    )
    assert item_before["requirement"] == 1000
    assert item_before["deficit"] == 400

    updated = await client.put(
        "/api/v1/admin/params",
        headers=auth_header(token),
        json={
            "category_a": 2,
            "category_b": 1.5,
            "category_c": 2,
            "remote_warehouse": 1.5,
            "pallet_multiple": False,
        },
    )
    assert updated.status_code == 200, updated.text

    after = await client.get(
        "/api/v1/logistics/normative/dashboard",
        params={"warehouse_code": warehouse_code},
        headers=auth_header(token),
    )
    assert after.status_code == 200, after.text
    item_after = _item(
        _warehouse(after.json()["data"], warehouse_code), TEST_PRODUCT_DEFICIT
    )
    assert item_after["normative_quantity"] == 1000
    assert item_after["requirement"] == 2000
    assert item_after["deficit"] == 1400


def test_calculate_requirement_factors() -> None:
    assert calculate_requirement(Decimal("1000"), "A", False) == Decimal("1000")
    assert calculate_requirement(Decimal("1000"), "B", False) == Decimal("1500")
    assert calculate_requirement(Decimal("1000"), "C", False) == Decimal("2000")
    assert calculate_requirement(Decimal("1000"), "A", True) == Decimal("1500")
    assert calculate_requirement(Decimal("1000"), "B", True) == Decimal("2250")
    assert calculate_requirement(Decimal("1000"), "C", True) == Decimal("3000")


async def test_dashboard_requirement_uses_category_and_distance(
    client: AsyncClient,
    logistics_user: AuthUser,
    logistics_catalog: dict,
) -> None:
    warehouse_code = logistics_catalog["warehouse_code"]
    async with AsyncSessionLocal() as session:
        warehouse = await session.get(Object, warehouse_code)
        assert warehouse is not None
        warehouse.long_distance = True
        await session.commit()
    try:
        token = await login_token(client, logistics_user)
        response = await client.get(
            "/api/v1/logistics/normative/dashboard",
            params={"warehouse_code": warehouse_code},
            headers=auth_header(token),
        )
        assert response.status_code == 200, response.text
        warehouse = _warehouse(response.json()["data"], warehouse_code)
        assert warehouse["long_distance"] is True
        assert warehouse["long_distance_message"] == LONG_DISTANCE_MESSAGE
        item = _item(warehouse, TEST_PRODUCT_DEFICIT)
        assert item["normative_quantity"] == 1000
        assert item["requirement"] == 1500
        assert item["plan"] == 600
        assert item["deficit"] == 900
        assert item["category"] == "A"
    finally:
        async with AsyncSessionLocal() as session:
            warehouse = await session.get(Object, warehouse_code)
            assert warehouse is not None
            warehouse.long_distance = False
            await session.commit()


async def test_dashboard_remote_requirement_multiplies_category_and_distance(
    client: AsyncClient,
    logistics_user: AuthUser,
    logistics_catalog: dict,
) -> None:
    warehouse_code = logistics_catalog["warehouse_code"]
    async with AsyncSessionLocal() as session:
        warehouse = await session.get(Object, warehouse_code)
        assert warehouse is not None
        warehouse.long_distance = True
        ok_product = await session.get(Product, TEST_PRODUCT_OK)
        assert ok_product is not None
        ok_product.category = "B"
        await session.commit()
    try:
        token = await login_token(client, logistics_user)
        response = await client.get(
            "/api/v1/logistics/normative/dashboard",
            params={"warehouse_code": warehouse_code, "filter_mode": "all"},
            headers=auth_header(token),
        )
        assert response.status_code == 200, response.text
        warehouse = _warehouse(response.json()["data"], warehouse_code)
        assert warehouse["long_distance"] is True
        category_a = _item(warehouse, TEST_PRODUCT_DEFICIT)
        assert category_a["category"] == "A"
        assert category_a["normative_quantity"] == 1000
        assert category_a["requirement"] == 1500
        category_b = _item(warehouse, TEST_PRODUCT_OK)
        assert category_b["category"] == "B"
        assert category_b["normative_quantity"] == 500
        assert category_b["requirement"] == 1125
        assert category_b["plan"] == 500
        assert category_b["deficit"] == 625
    finally:
        async with AsyncSessionLocal() as session:
            warehouse = await session.get(Object, warehouse_code)
            assert warehouse is not None
            warehouse.long_distance = False
            ok_product = await session.get(Product, TEST_PRODUCT_OK)
            assert ok_product is not None
            ok_product.category = "A"
            await session.commit()


async def test_dashboard_filter_deficit_only(
    client: AsyncClient,
    logistics_user: AuthUser,
    logistics_catalog: dict,
) -> None:
    token = await login_token(client, logistics_user)
    response = await client.get(
        "/api/v1/logistics/normative/dashboard",
        params={"filter_mode": "deficit_only"},
        headers=auth_header(token),
    )
    assert response.status_code == 200, response.text
    warehouse = _warehouse(response.json()["data"], logistics_catalog["warehouse_code"])
    codes = {item["product_code"] for item in warehouse["deficit_items"]}
    assert TEST_PRODUCT_DEFICIT in codes
    assert TEST_PRODUCT_OK not in codes
    assert all(
        item["deficit"] > 0 or item.get("hide_group_metrics")
        for item in warehouse["deficit_items"]
    )


async def test_dashboard_filter_all_includes_stock_without_normative(
    client: AsyncClient,
    logistics_user: AuthUser,
    logistics_catalog: dict,
) -> None:
    token = await login_token(client, logistics_user)
    response = await client.get(
        "/api/v1/logistics/normative/dashboard",
        params={
            "filter_mode": "all",
            "warehouse_code": logistics_catalog["warehouse_code"],
        },
        headers=auth_header(token),
    )
    assert response.status_code == 200, response.text
    warehouse = _warehouse(response.json()["data"], logistics_catalog["warehouse_code"])
    codes = {item["product_code"] for item in warehouse["deficit_items"]}
    assert TEST_PRODUCT_STOCK_ONLY in codes
    stock_only = _item(warehouse, TEST_PRODUCT_STOCK_ONLY)
    assert stock_only["normative_quantity"] == 0
    assert stock_only["available"] == 80
    assert stock_only["plan"] == 80
    assert stock_only["status"] == "ok"


async def test_dashboard_unit_conversion(
    client: AsyncClient,
    logistics_user: AuthUser,
    logistics_catalog: dict,
) -> None:
    token = await login_token(client, logistics_user)
    response = await client.get(
        "/api/v1/logistics/normative/dashboard",
        params={"unit": "т", "warehouse_code": logistics_catalog["warehouse_code"]},
        headers=auth_header(token),
    )
    assert response.status_code == 200, response.text
    warehouse = _warehouse(response.json()["data"], logistics_catalog["warehouse_code"])
    item = _item(warehouse, TEST_PRODUCT_DEFICIT)
    assert item["unit"] == "т"
    assert item["normative_quantity"] == pytest.approx(0.25)
    assert item["requirement"] == pytest.approx(0.25)
    assert item["available"] == pytest.approx(0.15)
    assert item["plan"] == pytest.approx(0.15)
    assert item["deficit"] == pytest.approx(0.1)


async def test_dashboard_allowed_for_commercial(
    client: AsyncClient,
    test_user: AuthUser,
    logistics_catalog: dict,
) -> None:
    token = await login_token(client, test_user)
    response = await client.get(
        "/api/v1/logistics/normative/dashboard",
        headers=auth_header(token),
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "success"


async def test_generate_orders_forbidden_for_commercial(
    client: AsyncClient,
    test_user: AuthUser,
    logistics_catalog: dict,
) -> None:
    token = await login_token(client, test_user)
    warehouse_code = logistics_catalog["warehouse_code"]
    response = await client.post(
        f"/api/v1/logistics/normative/{warehouse_code}/generate-orders",
        headers=auth_header(token),
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


async def test_generate_orders_returns_correct_structure(
    client: AsyncClient,
    logistics_user: AuthUser,
    logistics_catalog: dict,
) -> None:
    token = await login_token(client, logistics_user)
    warehouse_code = logistics_catalog["warehouse_code"]
    response = await client.post(
        f"/api/v1/logistics/normative/{warehouse_code}/generate-orders",
        headers=auth_header(token),
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["total_orders"] >= 1
    assert data["total_products"] >= 1
    order = next(
        item
        for item in data["orders"]
        if item["plant_code"] == logistics_catalog["plant_code"]
    )
    assert order["warehouse_code"] == warehouse_code
    assert order["warehouse_name"] == "Склад Ростов"
    assert order["estimated_delivery_days"] == 5
    product = next(
        item for item in order["items"] if item["product_code"] == TEST_PRODUCT_DEFICIT
    )
    assert product["product_name"] == "Тестовый подшипник логистики"
    assert product["deficit"] == 400
    assert product["unit"] == "шт"
    assert product["weight_kg"] == pytest.approx(0.25)
    ok_codes = {
        item["product_code"] for order in data["orders"] for item in order["items"]
    }
    assert TEST_PRODUCT_OK not in ok_codes


async def test_generate_orders_unknown_warehouse(
    client: AsyncClient,
    logistics_user: AuthUser,
    logistics_catalog: dict,
) -> None:
    token = await login_token(client, logistics_user)
    response = await client.post(
        "/api/v1/logistics/normative/9999/generate-orders",
        headers=auth_header(token),
    )
    assert response.status_code == 404


async def test_generate_orders_bulk_returns_selected_warehouses(
    client: AsyncClient,
    logistics_user: AuthUser,
    logistics_catalog: dict,
) -> None:
    token = await login_token(client, logistics_user)
    warehouse_code = logistics_catalog["warehouse_code"]
    response = await client.post(
        "/api/v1/logistics/normative/generate-orders",
        headers=auth_header(token),
        json={"warehouse_codes": [warehouse_code, 2002]},
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["total_orders"] >= 1
    assert {order["warehouse_code"] for order in data["orders"]} <= {
        warehouse_code,
        2002,
    }
    product = next(
        item
        for order in data["orders"]
        for item in order["items"]
        if item["product_code"] == TEST_PRODUCT_DEFICIT
    )
    assert product["deficit"] == 400


async def test_generate_orders_bulk_requires_warehouse_codes(
    client: AsyncClient,
    logistics_user: AuthUser,
    logistics_catalog: dict,
) -> None:
    token = await login_token(client, logistics_user)
    empty = await client.post(
        "/api/v1/logistics/normative/generate-orders",
        headers=auth_header(token),
        json={"warehouse_codes": []},
    )
    assert empty.status_code == 400
    missing = await client.post(
        "/api/v1/logistics/normative/generate-orders",
        headers=auth_header(token),
        json={},
    )
    assert missing.status_code == 400


async def test_generate_orders_bulk_unknown_warehouse(
    client: AsyncClient,
    logistics_user: AuthUser,
    logistics_catalog: dict,
) -> None:
    token = await login_token(client, logistics_user)
    response = await client.post(
        "/api/v1/logistics/normative/generate-orders",
        headers=auth_header(token),
        json={"warehouse_codes": [9999]},
    )
    assert response.status_code == 404


async def test_export_excel_returns_file(
    client: AsyncClient,
    logistics_user: AuthUser,
    logistics_catalog: dict,
) -> None:
    token = await login_token(client, logistics_user)
    response = await client.get(
        "/api/v1/logistics/normative/export",
        params={"warehouse_code": logistics_catalog["warehouse_code"]},
        headers=auth_header(token),
    )
    assert response.status_code == 200, response.text
    assert "spreadsheetml.sheet" in response.headers["content-type"]
    workbook = load_workbook(BytesIO(response.content))
    sheet = workbook.active
    header = [cell.value for cell in next(sheet.iter_rows(min_row=1, max_row=1))]
    assert header == [
        "Склад",
        "Артикул",
        "Название",
        "Норматив",
        "Потребность",
        "Доступно",
        "Доступно + Запланировано",
        "Дефицит",
        "Ед",
        "Клиент",
    ]
    rows = [
        [cell.value for cell in row]
        for row in sheet.iter_rows(min_row=2, values_only=False)
    ]
    matched = next(row for row in rows if row[1] == TEST_PRODUCT_DEFICIT)
    assert matched[0] == "Склад Ростов"
    assert matched[2] == "Тестовый подшипник логистики"
    assert matched[3] == 1000
    assert matched[4] == 1000
    assert matched[5] == 600
    assert matched[6] == 600
    assert matched[7] == 400
    assert matched[8] == "шт"
    assert matched[9] == CLIENT_NAME


AVAILABLE_HEADERS = [
    "КССС материала",
    "Завод",
    "Склад",
    "Запас",
    "Всего поступлений",
    "Доступно из запаса",
]
MOVING_HEADERS = [
    "Стат. движ.мат.",
    "Транспортный заказ",
    "№ продукта",
    "Вес нетто",
    "Открыто (не включено в ИП)",
    "Склад-получатель",
    "ПродажнЕдиница",
]


def _sheet(headers: list[str], rows: list[dict]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(headers)
    for row in rows:
        sheet.append([row.get(header) for header in headers])
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _available_row(
    *,
    product_code: int | str,
    warehouse: str,
    available: float | str | None,
    plant: int | float | str = 2401,
    full_stock: float | str | None = None,
    on_way: float | str | None = 0,
) -> dict:
    return {
        "КССС материала": product_code,
        "Завод": plant,
        "Склад": warehouse,
        "Запас": available if full_stock is None else full_stock,
        "Всего поступлений": on_way,
        "Доступно из запаса": available,
    }


def _moving_row(
    *,
    product_code: int | str,
    warehouse: str,
    opened: float | str | None = 0,
    net: float | str | None = 0,
    status: str | None = None,
    transport: str | None = None,
    unit: str | None = "КГ",
) -> dict:
    return {
        "Стат. движ.мат.": status,
        "Транспортный заказ": transport,
        "№ продукта": product_code,
        "Вес нетто": net,
        "Открыто (не включено в ИП)": opened,
        "Склад-получатель": warehouse,
        "ПродажнЕдиница": unit,
    }


def _upload_files(
    available_rows: list[dict],
    moving_rows: list[dict] | None = None,
    *,
    available_name: str = "available.xlsx",
    moving_name: str = "moving.xlsx",
    available_content: bytes | None = None,
    moving_content: bytes | None = None,
) -> dict:
    content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return {
        "available_file": (
            available_name,
            available_content
            if available_content is not None
            else _sheet(AVAILABLE_HEADERS, available_rows),
            content_type,
        ),
        "moving_file": (
            moving_name,
            moving_content
            if moving_content is not None
            else _sheet(MOVING_HEADERS, moving_rows or []),
            content_type,
        ),
    }


async def test_upload_balances_stores_kg_and_recalculates_plan(
    client: AsyncClient,
    logistics_user: AuthUser,
    logistics_catalog: dict,
) -> None:
    token = await login_token(client, logistics_user)
    warehouse = logistics_catalog["warehouse_code"]
    response = await client.post(
        "/api/v1/logistics/normative/upload",
        headers=auth_header(token),
        files=_upload_files(
            [
                _available_row(
                    product_code=TEST_PRODUCT_DEFICIT,
                    warehouse="F005",
                    full_stock=100,
                    available=40,
                    on_way=10,
                ),
                _available_row(
                    product_code=TEST_PRODUCT_STOCK_ONLY,
                    warehouse="F005",
                    full_stock=10,
                    available=10,
                    on_way=0,
                ),
            ],
            [
                _moving_row(
                    product_code=TEST_PRODUCT_DEFICIT,
                    warehouse="F005",
                    opened=4,
                    unit="ШТ",
                ),
                _moving_row(
                    product_code=TEST_PRODUCT_DEFICIT,
                    warehouse="F005",
                    opened=2,
                    unit="КГ",
                ),
                _moving_row(
                    product_code=TEST_PRODUCT_DEFICIT,
                    warehouse="F005",
                    status="A",
                    net=3,
                ),
                _moving_row(
                    product_code=TEST_PRODUCT_DEFICIT,
                    warehouse="F005",
                    status="A",
                    transport="6100",
                    net=7,
                ),
                _moving_row(
                    product_code=TEST_PRODUCT_DEFICIT,
                    warehouse="F005",
                    status="C",
                    opened=100,
                    net=100,
                ),
                _moving_row(
                    product_code=TEST_PRODUCT_DEFICIT,
                    warehouse="F005",
                    status="А",
                    net=1.5,
                    unit="ШТ",
                ),
            ],
        ),
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["uploaded"] == 2
    assert data["updated"] == 2
    assert data["created"] == 0
    assert data["errors"] == 0
    assert data["message"] == "Загружено 2"

    async with AsyncSessionLocal() as session:
        stored = await session.get(AvailableBalance, (warehouse, TEST_PRODUCT_DEFICIT))
        plain = await session.get(
            AvailableBalance, (warehouse, TEST_PRODUCT_STOCK_ONLY)
        )
        removed = await session.get(AvailableBalance, (warehouse, TEST_PRODUCT_OK))
        assert stored is not None
        assert stored.full_stock == Decimal("100.00")
        assert stored.available == Decimal("40.00")
        assert stored.on_way == Decimal("10.00")
        assert stored.no_ready == Decimal("3.00")
        assert stored.ready == Decimal("4.50")
        assert stored.collected == Decimal("7.00")
        assert stored.plan == Decimal("64.50")
        assert stored.unit == "кг"
        assert stored.source == "excel_upload"
        assert plain is not None
        assert plain.plan == Decimal("10.00")
        assert plain.no_ready == Decimal("0.00")
        assert removed is None
        snapshot = await session.scalar(
            select(AvailableBalanceHistory)
            .where(
                AvailableBalanceHistory.warehouse_code == warehouse,
                AvailableBalanceHistory.product_code == TEST_PRODUCT_DEFICIT,
            )
            .order_by(AvailableBalanceHistory.snapshot_at.desc())
        )
        assert snapshot is not None
        assert snapshot.full_stock == Decimal("100.00")
        assert snapshot.available == Decimal("40.00")
        assert snapshot.plan == Decimal("64.50")
        assert snapshot.unit == "кг"

    dashboard = await client.get(
        "/api/v1/logistics/normative/dashboard",
        params={"warehouse_code": warehouse, "unit": "шт"},
        headers=auth_header(token),
    )
    assert dashboard.status_code == 200, dashboard.text
    item = _item(
        _warehouse(dashboard.json()["data"], warehouse),
        TEST_PRODUCT_DEFICIT,
    )
    assert item["stock_unit"] == "КГ"
    assert item["available"] == 160
    assert item["no_ready"] == 12
    assert item["ready"] == 18
    assert item["collected"] == 28
    assert item["on_way"] == 40
    assert item["plan"] == 258
    assert item["plan"] == pytest.approx(
        item["available"]
        + item["no_ready"]
        + item["ready"]
        + item["collected"]
        + item["on_way"]
    )

    tons = await client.get(
        "/api/v1/logistics/normative/dashboard",
        params={"warehouse_code": warehouse, "unit": "т"},
        headers=auth_header(token),
    )
    assert tons.status_code == 200, tons.text
    tons_item = _item(
        _warehouse(tons.json()["data"], warehouse),
        TEST_PRODUCT_DEFICIT,
    )
    assert tons_item["available"] == pytest.approx(0.04)
    assert tons_item["no_ready"] == pytest.approx(0.003)
    assert tons_item["ready"] == pytest.approx(0.0045)
    assert tons_item["collected"] == pytest.approx(0.007)
    assert tons_item["on_way"] == pytest.approx(0.01)
    assert tons_item["plan"] == pytest.approx(0.0645)
    assert tons_item["plan"] == pytest.approx(
        tons_item["available"]
        + tons_item["no_ready"]
        + tons_item["ready"]
        + tons_item["collected"]
        + tons_item["on_way"]
    )


async def test_upload_balances_replaces_warehouse_and_keeps_others(
    client: AsyncClient,
    logistics_user: AuthUser,
    logistics_catalog: dict,
) -> None:
    token = await login_token(client, logistics_user)
    other_warehouse = 2002
    async with AsyncSessionLocal() as session:
        session.add(
            AvailableBalance(
                warehouse_code=other_warehouse,
                product_code=TEST_PRODUCT_DEFICIT,
                available=Decimal("90"),
                plan=Decimal("90"),
                unit="шт",
                source="manual",
            )
        )
        await session.commit()

    response = await client.post(
        "/api/v1/logistics/normative/upload",
        headers=auth_header(token),
        files=_upload_files(
            [
                _available_row(
                    product_code=TEST_PRODUCT_DEFICIT,
                    warehouse="F005",
                    full_stock=111,
                    available=111,
                    on_way=0,
                )
            ]
        ),
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["uploaded"] == 1
    assert data["errors"] == 0

    async with AsyncSessionLocal() as session:
        rewritten = await session.get(
            AvailableBalance,
            (logistics_catalog["warehouse_code"], TEST_PRODUCT_DEFICIT),
        )
        gone_ok = await session.get(
            AvailableBalance,
            (logistics_catalog["warehouse_code"], TEST_PRODUCT_OK),
        )
        gone_stock = await session.get(
            AvailableBalance,
            (logistics_catalog["warehouse_code"], TEST_PRODUCT_STOCK_ONLY),
        )
        kept_other = await session.get(
            AvailableBalance,
            (other_warehouse, TEST_PRODUCT_DEFICIT),
        )
        assert rewritten is not None
        assert rewritten.available == Decimal("111")
        assert rewritten.plan == Decimal("111")
        assert rewritten.source == "excel_upload"
        assert gone_ok is None
        assert gone_stock is None
        assert kept_other is not None
        assert kept_other.available == Decimal("90")
        await session.execute(
            delete(AvailableBalance).where(
                AvailableBalance.warehouse_code == other_warehouse,
                AvailableBalance.product_code == TEST_PRODUCT_DEFICIT,
            )
        )
        await session.commit()


async def test_sync_info_empty_before_upload(
    client: AsyncClient,
    logistics_user: AuthUser,
    logistics_catalog: dict,
) -> None:
    token = await login_token(client, logistics_user)
    response = await client.get(
        "/api/v1/logistics/normative/sync-info",
        headers=auth_header(token),
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["last_balances_sync_at"] is None
    assert data["last_balances_sync_by"] is None


async def test_sync_info_after_upload(
    client: AsyncClient,
    logistics_user: AuthUser,
    logistics_catalog: dict,
) -> None:
    token = await login_token(client, logistics_user)
    uploaded = await client.post(
        "/api/v1/logistics/normative/upload",
        headers=auth_header(token),
        files=_upload_files(
            [
                _available_row(
                    product_code=TEST_PRODUCT_DEFICIT,
                    warehouse="F005",
                    available=1,
                )
            ]
        ),
    )
    assert uploaded.status_code == 200, uploaded.text

    response = await client.get(
        "/api/v1/logistics/normative/sync-info",
        headers=auth_header(token),
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["last_balances_sync_at"] is not None
    assert data["last_balances_sync_by"]["id"] == str(logistics_user.id)
    assert data["last_balances_sync_by"]["full_name"] == logistics_user.full_name
    assert data["last_balances_sync_by"]["role"] == "logistics"


async def test_sync_info_allowed_for_commercial(
    client: AsyncClient,
    test_user: AuthUser,
    logistics_catalog: dict,
) -> None:
    token = await login_token(client, test_user)
    response = await client.get(
        "/api/v1/logistics/normative/sync-info",
        headers=auth_header(token),
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "success"


async def test_upload_balances_forbidden_for_commercial(
    client: AsyncClient,
    test_user: AuthUser,
    logistics_catalog: dict,
) -> None:
    token = await login_token(client, test_user)
    files = _upload_files(
        [
            _available_row(
                product_code=TEST_PRODUCT_DEFICIT,
                warehouse="F005",
                available=1,
            )
        ]
    )
    preview = await client.post(
        "/api/v1/logistics/normative/preview",
        headers=auth_header(token),
        files=files,
    )
    assert preview.status_code == 403
    assert preview.json()["error"]["code"] == "FORBIDDEN"
    response = await client.post(
        "/api/v1/logistics/normative/upload",
        headers=auth_header(token),
        files=files,
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


async def test_upload_balances_rejects_non_excel(
    client: AsyncClient,
    logistics_user: AuthUser,
    logistics_catalog: dict,
) -> None:
    token = await login_token(client, logistics_user)
    response = await client.post(
        "/api/v1/logistics/normative/upload",
        headers=auth_header(token),
        files=_upload_files(
            [],
            [],
            available_name="balances.csv",
            available_content=b"not-excel",
        ),
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_FILE"


async def test_upload_converts_sales_unit_and_rejects_unknown(
    client: AsyncClient,
    logistics_user: AuthUser,
    logistics_catalog: dict,
) -> None:
    token = await login_token(client, logistics_user)
    warehouse = logistics_catalog["warehouse_code"]
    available_rows = [
        _available_row(
            product_code=TEST_PRODUCT_DEFICIT,
            warehouse="F005",
            full_stock=0,
            available=0,
            on_way=0,
        )
    ]
    rejected_files = _upload_files(
        available_rows,
        [
            _moving_row(
                product_code=TEST_PRODUCT_DEFICIT,
                warehouse="F005",
                opened=2,
                unit="ЛИТР",
            )
        ],
    )
    preview = await client.post(
        "/api/v1/logistics/normative/preview",
        headers=auth_header(token),
        files=rejected_files,
    )
    assert preview.status_code == 200, preview.text
    preview_data = preview.json()["data"]
    assert preview_data["can_upload"] is False
    assert any(
        "ПродажнЕдиница" in item["message"] for item in preview_data["error_details"]
    )
    rejected = await client.post(
        "/api/v1/logistics/normative/upload",
        headers=auth_header(token),
        files=rejected_files,
    )
    assert rejected.status_code == 400
    async with AsyncSessionLocal() as session:
        untouched = await session.get(
            AvailableBalance, (warehouse, TEST_PRODUCT_DEFICIT)
        )
        assert untouched is not None
        assert untouched.available == Decimal("600")
        assert untouched.source == "manual"

    uploaded = await client.post(
        "/api/v1/logistics/normative/upload",
        headers=auth_header(token),
        files=_upload_files(
            available_rows,
            [
                _moving_row(
                    product_code=TEST_PRODUCT_DEFICIT,
                    warehouse="F005",
                    opened=2,
                    unit="т",
                ),
                _moving_row(
                    product_code=TEST_PRODUCT_DEFICIT,
                    warehouse="F005",
                    opened=4,
                    unit="ШТ",
                ),
            ],
        ),
    )
    assert uploaded.status_code == 200, uploaded.text
    async with AsyncSessionLocal() as session:
        stored = await session.get(AvailableBalance, (warehouse, TEST_PRODUCT_DEFICIT))
        assert stored is not None
        assert stored.no_ready == Decimal("2001.00")
        assert stored.plan == Decimal("2001.00")
        assert stored.unit == "кг"


def test_parse_excel_codes_normalizes_float_and_string() -> None:
    assert _parse_int_cell(2401, "завод") == 2401
    assert _parse_int_cell(2401.0, "завод") == 2401
    assert _parse_int_cell("2401.0", "завод") == 2401
    assert _parse_int_cell("2401", "завод") == 2401
    assert _parse_warehouse_code("F005") == "F005"
    assert _parse_warehouse_code("f005") == "F005"
    assert _parse_warehouse_code(2401.0) == "2401"
    assert _parse_quantity(-120.5, "available") == Decimal("-120.50")
    assert _parse_quantity("-80,00", "plan") == Decimal("-80.00")
    assert _parse_quantity(0, "available") == Decimal("0.00")


async def test_upload_balances_finds_erp_plant_code_on_warehouse(
    client: AsyncClient,
    logistics_user: AuthUser,
    logistics_catalog: dict,
) -> None:
    """erp_plant_code may live on warehouses when there is no type=plant row."""
    token = await login_token(client, logistics_user)
    warehouse_code = 2002
    erp_plant_only_on_warehouse = 2410
    previous_plant_code = None
    async with AsyncSessionLocal() as session:
        warehouse = await session.get(Object, warehouse_code)
        assert warehouse is not None
        previous_plant_code = warehouse.erp_plant_code
        warehouse.erp_plant_code = erp_plant_only_on_warehouse
        await session.commit()

    try:
        response = await client.post(
            "/api/v1/logistics/normative/upload",
            headers=auth_header(token),
            files=_upload_files(
                [
                    _available_row(
                        product_code=TEST_PRODUCT_DEFICIT,
                        plant=2410.0,
                        warehouse="F006",
                        full_stock=33,
                        available=33,
                        on_way=11,
                    )
                ]
            ),
        )
        assert response.status_code == 200, response.text
        data = response.json()["data"]
        assert data["uploaded"] == 1
        assert data["errors"] == 0
        assert data["error_details"] == []

        async with AsyncSessionLocal() as session:
            stored = await session.get(
                AvailableBalance,
                (warehouse_code, TEST_PRODUCT_DEFICIT),
            )
            assert stored is not None
            assert stored.available == Decimal("33")
            assert stored.on_way == Decimal("11")
            assert stored.plan == Decimal("44")
            await session.execute(
                delete(AvailableBalance).where(
                    AvailableBalance.warehouse_code == warehouse_code,
                    AvailableBalance.product_code == TEST_PRODUCT_DEFICIT,
                )
            )
            await session.commit()
    finally:
        async with AsyncSessionLocal() as session:
            warehouse = await session.get(Object, warehouse_code)
            if warehouse is not None:
                warehouse.erp_plant_code = previous_plant_code
                await session.commit()


async def test_upload_balances_allows_negative_available(
    client: AsyncClient,
    logistics_user: AuthUser,
    logistics_catalog: dict,
) -> None:
    token = await login_token(client, logistics_user)
    warehouse = logistics_catalog["warehouse_code"]
    files = _upload_files(
        [
            _available_row(
                product_code=TEST_PRODUCT_DEFICIT,
                warehouse="F005",
                full_stock=1,
                available=-80,
                on_way=0,
            )
        ]
    )
    preview = await client.post(
        "/api/v1/logistics/normative/preview",
        headers=auth_header(token),
        files=files,
    )
    assert preview.status_code == 200, preview.text
    data = preview.json()["data"]
    assert data["can_upload"] is True
    assert data["errors"] == 0
    assert data["error_details"] == []
    assert data["available_preview"][0]["available"] == "-80"
    response = await client.post(
        "/api/v1/logistics/normative/upload",
        headers=auth_header(token),
        files=files,
    )
    assert response.status_code == 200, response.text
    async with AsyncSessionLocal() as session:
        stored = await session.get(AvailableBalance, (warehouse, TEST_PRODUCT_DEFICIT))
        assert stored is not None
        assert stored.available == Decimal("-80")
        assert stored.plan == Decimal("-80")
        assert stored.source == "excel_upload"


async def test_upload_skips_unknown_articles_without_blocking_valid_rows(
    client: AsyncClient,
    logistics_user: AuthUser,
    logistics_catalog: dict,
) -> None:
    token = await login_token(client, logistics_user)
    warehouse = logistics_catalog["warehouse_code"]
    unknown = 99999999
    files = _upload_files(
        [
            _available_row(
                product_code=TEST_PRODUCT_DEFICIT,
                warehouse="F005",
                full_stock=10,
                available=4,
                on_way=1,
            ),
            _available_row(
                product_code=unknown,
                warehouse="F005",
                full_stock=7,
                available=-2,
                on_way=0,
            ),
        ],
        [
            _moving_row(product_code=unknown, warehouse="F005", opened=3),
            _moving_row(
                product_code=TEST_PRODUCT_DEFICIT,
                warehouse="F005",
                opened=2,
            ),
        ],
    )
    preview = await client.post(
        "/api/v1/logistics/normative/preview",
        headers=auth_header(token),
        files=files,
    )
    assert preview.status_code == 200, preview.text
    data = preview.json()["data"]
    assert data["can_upload"] is True
    assert data["errors"] == 0
    assert data["warnings"] == 2
    assert all("не найден" in item["message"] for item in data["warning_details"])
    response = await client.post(
        "/api/v1/logistics/normative/upload",
        headers=auth_header(token),
        files=files,
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["warnings"] == 2
    async with AsyncSessionLocal() as session:
        stored = await session.get(AvailableBalance, (warehouse, TEST_PRODUCT_DEFICIT))
        missing = await session.get(AvailableBalance, (warehouse, unknown))
        assert stored is not None
        assert stored.available == Decimal("4")
        assert stored.no_ready == Decimal("2")
        assert stored.plan == Decimal("7")
        assert missing is None

    only_unknown = _upload_files(
        [
            _available_row(
                product_code=unknown,
                warehouse="F005",
                full_stock=1,
                available=1,
            )
        ]
    )
    blocked = await client.post(
        "/api/v1/logistics/normative/preview",
        headers=auth_header(token),
        files=only_unknown,
    )
    assert blocked.json()["data"]["can_upload"] is False
    assert blocked.json()["data"]["warnings"] == 1
    rejected = await client.post(
        "/api/v1/logistics/normative/upload",
        headers=auth_header(token),
        files=only_unknown,
    )
    assert rejected.status_code == 400
    async with AsyncSessionLocal() as session:
        stored = await session.get(AvailableBalance, (warehouse, TEST_PRODUCT_DEFICIT))
        assert stored is not None
        assert stored.available == Decimal("4")


async def test_upload_rejects_duplicates_missing_columns_and_cross_check(
    client: AsyncClient,
    logistics_user: AuthUser,
    logistics_catalog: dict,
) -> None:
    token = await login_token(client, logistics_user)
    warehouse = logistics_catalog["warehouse_code"]
    duplicate = _upload_files(
        [
            _available_row(
                product_code=TEST_PRODUCT_DEFICIT,
                warehouse="F005",
                available=1,
            ),
            _available_row(
                product_code=TEST_PRODUCT_DEFICIT,
                warehouse="F005",
                available=2,
            ),
        ]
    )
    preview = await client.post(
        "/api/v1/logistics/normative/preview",
        headers=auth_header(token),
        files=duplicate,
    )
    assert preview.status_code == 200, preview.text
    assert any(
        "Повтор пары" in item["message"]
        for item in preview.json()["data"]["error_details"]
    )

    missing_column = _sheet(
        ["КССС материала", "Завод", "Склад", "Доступно из запаса"],
        [
            {
                "КССС материала": TEST_PRODUCT_DEFICIT,
                "Завод": 2401,
                "Склад": "F005",
                "Доступно из запаса": 1,
            }
        ],
    )
    column_preview = await client.post(
        "/api/v1/logistics/normative/preview",
        headers=auth_header(token),
        files=_upload_files([], available_content=missing_column),
    )
    assert column_preview.status_code == 200, column_preview.text
    assert any(
        item["message"] == "Нет колонки «Запас»"
        for item in column_preview.json()["data"]["error_details"]
    )

    cross = _upload_files(
        [
            _available_row(
                product_code=TEST_PRODUCT_DEFICIT,
                warehouse="F005",
                available=1,
            )
        ],
        [
            _moving_row(product_code=TEST_PRODUCT_OK, warehouse="F005", opened=1),
            _moving_row(
                product_code=TEST_PRODUCT_DEFICIT,
                warehouse="F005",
                opened=1,
            ),
            _moving_row(
                product_code=TEST_PRODUCT_DEFICIT,
                warehouse="F005",
                opened=2,
            ),
        ],
    )
    cross_preview = await client.post(
        "/api/v1/logistics/normative/preview",
        headers=auth_header(token),
        files=cross,
    )
    assert cross_preview.status_code == 200, cross_preview.text
    cross_data = cross_preview.json()["data"]
    assert cross_data["can_upload"] is True
    assert cross_data["errors"] == 0
    assert not any(
        "отсутствует в файле" in item["message"]
        for item in cross_data["error_details"]
    )
    assert len(cross_data["available_preview"]) == 1
    assert len(cross_data["moving_preview"]) == 3

    many = _upload_files(
        [
            _available_row(
                product_code=TEST_PRODUCT_DEFICIT,
                warehouse="F005",
                available=index,
            )
            for index in range(12)
        ]
    )
    many_preview = await client.post(
        "/api/v1/logistics/normative/preview",
        headers=auth_header(token),
        files=many,
    )
    assert many_preview.status_code == 200, many_preview.text
    assert len(many_preview.json()["data"]["available_preview"]) == 10
    assert many_preview.json()["data"]["available_rows"] == 12

    async with AsyncSessionLocal() as session:
        stored = await session.get(AvailableBalance, (warehouse, TEST_PRODUCT_DEFICIT))
        assert stored is not None
        assert stored.available == Decimal("600")


async def test_upload_fills_missing_available_pair_with_zeros(
    client: AsyncClient,
    logistics_user: AuthUser,
    logistics_catalog: dict,
) -> None:
    token = await login_token(client, logistics_user)
    warehouse = logistics_catalog["warehouse_code"]
    other_warehouse = 2002
    async with AsyncSessionLocal() as session:
        session.add(
            AvailableBalance(
                warehouse_code=other_warehouse,
                product_code=TEST_PRODUCT_STOCK_ONLY,
                available=Decimal("77"),
                plan=Decimal("77"),
                unit="шт",
                source="manual",
            )
        )
        await session.commit()

    response = await client.post(
        "/api/v1/logistics/normative/upload",
        headers=auth_header(token),
        files=_upload_files(
            [
                _available_row(
                    product_code=TEST_PRODUCT_DEFICIT,
                    warehouse="F005",
                    full_stock=20,
                    available=10,
                    on_way=3,
                )
            ],
            [
                _moving_row(
                    product_code=TEST_PRODUCT_OK,
                    warehouse="F005",
                    opened=4,
                ),
                _moving_row(
                    product_code=TEST_PRODUCT_OK,
                    warehouse="F005",
                    status="A",
                    net=6,
                ),
                _moving_row(
                    product_code=TEST_PRODUCT_DEFICIT,
                    warehouse="F006",
                    opened=5,
                ),
            ],
        ),
    )
    assert response.status_code == 200, response.text
    async with AsyncSessionLocal() as session:
        same_warehouse = await session.get(
            AvailableBalance, (warehouse, TEST_PRODUCT_OK)
        )
        from_file = await session.get(
            AvailableBalance, (warehouse, TEST_PRODUCT_DEFICIT)
        )
        other_product = await session.get(
            AvailableBalance, (other_warehouse, TEST_PRODUCT_DEFICIT)
        )
        untouched = await session.get(
            AvailableBalance, (other_warehouse, TEST_PRODUCT_STOCK_ONLY)
        )
        removed = await session.get(
            AvailableBalance, (warehouse, TEST_PRODUCT_STOCK_ONLY)
        )
        assert same_warehouse is not None
        assert same_warehouse.full_stock == Decimal("0")
        assert same_warehouse.available == Decimal("0")
        assert same_warehouse.on_way == Decimal("0")
        assert same_warehouse.no_ready == Decimal("4")
        assert same_warehouse.ready == Decimal("6")
        assert same_warehouse.plan == Decimal("10")
        assert from_file is not None
        assert from_file.full_stock == Decimal("20")
        assert from_file.available == Decimal("10")
        assert from_file.on_way == Decimal("3")
        assert from_file.plan == Decimal("13")
        assert other_product is not None
        assert other_product.full_stock == Decimal("0")
        assert other_product.available == Decimal("0")
        assert other_product.on_way == Decimal("0")
        assert other_product.no_ready == Decimal("5")
        assert other_product.plan == Decimal("5")
        assert untouched is not None
        assert untouched.available == Decimal("77")
        assert untouched.source == "manual"
        assert removed is None


async def _clear_balance_history(*warehouse_codes: int) -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(AvailableBalanceHistory).where(
                AvailableBalanceHistory.warehouse_code.in_(warehouse_codes)
            )
        )
        await session.commit()


def _history_file(*rows: dict) -> dict:
    return _upload_files(list(rows))


async def test_upload_replaces_daily_balance_snapshot(
    client: AsyncClient,
    logistics_user: AuthUser,
    logistics_catalog: dict,
) -> None:
    warehouse = logistics_catalog["warehouse_code"]
    other = 2002
    await _clear_balance_history(warehouse, other)
    today = datetime.now(UTC).date()
    async with AsyncSessionLocal() as session:
        session.add(
            AvailableBalanceHistory(
                snapshot_date=today,
                snapshot_at=datetime.now(UTC),
                warehouse_code=other,
                product_code=TEST_PRODUCT_DEFICIT,
                available=Decimal("5.00"),
                plan=Decimal("5.00"),
                unit="шт",
                source="excel_upload",
                uploaded_by=logistics_user.id,
            )
        )
        await session.commit()

    token = await login_token(client, logistics_user)
    first = await client.post(
        "/api/v1/logistics/normative/upload",
        headers=auth_header(token),
        files=_history_file(
            _available_row(
                product_code=TEST_PRODUCT_DEFICIT,
                warehouse="F005",
                full_stock=15,
                available=10,
                on_way=2,
            ),
            _available_row(
                product_code=TEST_PRODUCT_OK,
                warehouse="F005",
                full_stock=3,
                available=3,
                on_way=0,
            ),
        ),
    )
    assert first.status_code == 200, first.text

    async with AsyncSessionLocal() as session:
        stored = (
            await session.scalars(
                select(AvailableBalanceHistory).where(
                    AvailableBalanceHistory.warehouse_code == warehouse,
                    AvailableBalanceHistory.snapshot_date == today,
                )
            )
        ).all()
        by_product = {row.product_code: row for row in stored}
        assert set(by_product) == {TEST_PRODUCT_DEFICIT, TEST_PRODUCT_OK}
        assert by_product[TEST_PRODUCT_DEFICIT].available == Decimal("10.00")
        assert by_product[TEST_PRODUCT_DEFICIT].full_stock == Decimal("15.00")
        assert by_product[TEST_PRODUCT_DEFICIT].plan == Decimal("12.00")
        assert by_product[TEST_PRODUCT_DEFICIT].unit == "кг"
        assert by_product[TEST_PRODUCT_DEFICIT].source == "excel_upload"
        assert by_product[TEST_PRODUCT_DEFICIT].uploaded_by == logistics_user.id
        assert by_product[TEST_PRODUCT_OK].unit == "кг"
        kept = await session.scalar(
            select(AvailableBalanceHistory).where(
                AvailableBalanceHistory.warehouse_code == other,
                AvailableBalanceHistory.snapshot_date == today,
            )
        )
        assert kept is not None
        assert kept.available == Decimal("5.00")

    second = await client.post(
        "/api/v1/logistics/normative/upload",
        headers=auth_header(token),
        files=_history_file(
            _available_row(
                product_code=TEST_PRODUCT_DEFICIT,
                warehouse="F005",
                full_stock=30,
                available=21,
                on_way=1,
            )
        ),
    )
    assert second.status_code == 200, second.text

    async with AsyncSessionLocal() as session:
        stored = (
            await session.scalars(
                select(AvailableBalanceHistory).where(
                    AvailableBalanceHistory.warehouse_code == warehouse,
                    AvailableBalanceHistory.snapshot_date == today,
                )
            )
        ).all()
        assert [row.product_code for row in stored] == [TEST_PRODUCT_DEFICIT]
        assert stored[0].available == Decimal("21.00")
        assert stored[0].plan == Decimal("22.00")
        balance_gone = await session.get(AvailableBalance, (warehouse, TEST_PRODUCT_OK))
        balance_kept = await session.get(
            AvailableBalance, (warehouse, TEST_PRODUCT_DEFICIT)
        )
        other_snapshot = await session.scalar(
            select(AvailableBalanceHistory).where(
                AvailableBalanceHistory.warehouse_code == other
            )
        )
        assert balance_gone is None
        assert balance_kept is not None
        assert balance_kept.available == Decimal("21.00")
        assert balance_kept.plan == Decimal("22.00")
        assert balance_kept.source == "excel_upload"
        assert other_snapshot is not None
        await session.execute(
            delete(AvailableBalanceHistory).where(
                AvailableBalanceHistory.warehouse_code == other
            )
        )
        await session.commit()


async def test_balance_history_filters_for_any_role(
    client: AsyncClient,
    logistics_user: AuthUser,
    test_user: AuthUser,
    guest_user: AuthUser,
    logistics_catalog: dict,
) -> None:
    warehouse = logistics_catalog["warehouse_code"]
    await _clear_balance_history(warehouse)
    token = await login_token(client, logistics_user)
    uploaded = await client.post(
        "/api/v1/logistics/normative/upload",
        headers=auth_header(token),
        files=_history_file(
            _available_row(
                product_code=TEST_PRODUCT_DEFICIT,
                warehouse="F005",
                full_stock=12,
                available=8,
                on_way=1,
            ),
            _available_row(
                product_code=TEST_PRODUCT_STOCK_ONLY,
                warehouse="F005",
                available=1,
            ),
        ),
    )
    assert uploaded.status_code == 200, uploaded.text
    today = datetime.now(UTC).date()
    async with AsyncSessionLocal() as session:
        session.add(
            AvailableBalanceHistory(
                snapshot_date=today - timedelta(days=2),
                snapshot_at=datetime.now(UTC) - timedelta(days=2),
                warehouse_code=warehouse,
                product_code=TEST_PRODUCT_DEFICIT,
                available=Decimal("1.00"),
                plan=Decimal("1.00"),
                unit="ШТ",
                source="excel_upload",
                uploaded_by=logistics_user.id,
            )
        )
        await session.commit()

    commercial = await login_token(client, test_user)
    response = await client.get(
        "/api/v1/logistics/normative/history",
        params={
            "warehouse_code": warehouse,
            "product_code": TEST_PRODUCT_DEFICIT,
            "date_from": today.isoformat(),
            "date_to": today.isoformat(),
        },
        headers=auth_header(commercial),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["meta"]["total"] == 1
    assert body["data"][0]["available"] == 8
    assert body["data"][0]["plan"] == 9
    assert body["data"][0]["full_stock"] == 12
    assert body["data"][0]["product_code"] == TEST_PRODUCT_DEFICIT
    assert body["data"][0]["product_name"] == "Тестовый подшипник логистики"
    assert body["data"][0]["warehouse_name"] == "Склад Ростов"

    dates_response = await client.get(
        "/api/v1/logistics/normative/history/dates",
        headers=auth_header(commercial),
    )
    assert dates_response.status_code == 200, dates_response.text
    snapshot_dates = dates_response.json()["data"]
    assert today.isoformat() in snapshot_dates
    assert (today - timedelta(days=2)).isoformat() in snapshot_dates
    assert snapshot_dates == sorted(snapshot_dates, reverse=True)

    guest = await login_token(client, guest_user)
    guest_response = await client.get(
        "/api/v1/logistics/normative/history",
        params={"warehouse_code": warehouse, "date_from": today.isoformat()},
        headers=auth_header(guest),
    )
    assert guest_response.status_code == 200, guest_response.text
    assert guest_response.json()["meta"]["total"] == 2

    invalid = await client.get(
        "/api/v1/logistics/normative/history",
        params={"date_from": "2026-10-10", "date_to": "2026-10-01"},
        headers=auth_header(commercial),
    )
    assert invalid.status_code == 400
    assert invalid.json()["error"]["code"] == "VALIDATION_ERROR"
