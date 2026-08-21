from datetime import date
from decimal import Decimal
from io import BytesIO
from uuid import uuid4

import pytest
from httpx import AsyncClient
from openpyxl import Workbook, load_workbook
from sqlalchemy import delete, select

from app.core.database import AsyncSessionLocal
from app.models.available_balance import AvailableBalance
from app.models.normative import Normative
from app.models.product import Product
from app.models.request import Request
from app.models.request_item import RequestItem
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
                category="B",
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
                category="B",
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
    assert item["available"] == 600
    assert item["plan"] == 600
    assert item["deficit"] == 400
    assert item["unit"] == "шт"
    assert item["status"] == "warning"
    assert item["client_name"] == CLIENT_NAME
    assert warehouse["deficit_count"] >= 1
    assert body["summary"]["deficit_products"] >= 1


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
    assert all(item["deficit"] > 0 for item in warehouse["deficit_items"])


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
        "Доступно",
        "Запланировано",
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
    assert matched[4] == 600
    assert matched[5] == 600
    assert matched[6] == 400
    assert matched[7] == "шт"
    assert matched[8] == CLIENT_NAME


def _balance_excel_row(
    *,
    product_code: int | str | None,
    plant: int | str | None,
    warehouse: str | None,
    available: float | str | None,
    plan: float | str | None,
) -> list:
    row: list = [None] * 20
    row[0] = product_code
    row[2] = plant
    row[4] = warehouse
    row[18] = available
    row[19] = plan
    return row


def _build_balances_xlsx(data_rows: list[list]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(
        _balance_excel_row(
            product_code="product_code",
            plant="erp_plant_code",
            warehouse="erp_warehouse_code",
            available="available",
            plan="plan",
        )
    )
    for row in data_rows:
        sheet.append(row)
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


async def test_upload_balances_upserts_and_reports_errors(
    client: AsyncClient,
    logistics_user: AuthUser,
    logistics_catalog: dict,
) -> None:
    token = await login_token(client, logistics_user)
    content = _build_balances_xlsx(
        [
            _balance_excel_row(
                product_code=TEST_PRODUCT_DEFICIT,
                plant=2401,
                warehouse="F005",
                available=500,
                plan=700,
            ),
            _balance_excel_row(
                product_code=TEST_PRODUCT_STOCK_ONLY,
                plant=2401,
                warehouse="F005",
                available=10,
                plan=15,
            ),
            _balance_excel_row(
                product_code=TEST_PRODUCT_OK,
                plant=2401,
                warehouse="X999",
                available=1,
                plan=1,
            ),
        ]
    )
    response = await client.post(
        "/api/v1/logistics/normative/upload",
        headers=auth_header(token),
        files={
            "file": (
                "balances.xlsx",
                content,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["uploaded"] == 2
    assert data["updated"] >= 1
    assert data["errors"] == 1
    assert data["message"] == "Загружено 2, ошибок 1"
    assert any("X999" in item["message"] for item in data["error_details"])

    dashboard = await client.get(
        "/api/v1/logistics/normative/dashboard",
        params={"warehouse_code": logistics_catalog["warehouse_code"]},
        headers=auth_header(token),
    )
    assert dashboard.status_code == 200, dashboard.text
    warehouse = _warehouse(
        dashboard.json()["data"], logistics_catalog["warehouse_code"]
    )
    item = _item(warehouse, TEST_PRODUCT_DEFICIT)
    assert item["available"] == 500
    assert item["plan"] == 700
    assert item["deficit"] == 300


async def test_upload_balances_forbidden_for_commercial(
    client: AsyncClient,
    test_user: AuthUser,
    logistics_catalog: dict,
) -> None:
    token = await login_token(client, test_user)
    content = _build_balances_xlsx(
        [
            _balance_excel_row(
                product_code=TEST_PRODUCT_DEFICIT,
                plant=2401,
                warehouse="F005",
                available=1,
                plan=1,
            )
        ]
    )
    response = await client.post(
        "/api/v1/logistics/normative/upload",
        headers=auth_header(token),
        files={
            "file": (
                "balances.xlsx",
                content,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
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
        files={"file": ("balances.csv", b"not-excel", "text/csv")},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_FILE"
