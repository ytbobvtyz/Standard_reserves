from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import delete, select

from app.core.database import AsyncSessionLocal
from app.models.available_balance import AvailableBalance
from app.models.normative import Normative
from app.models.product import Product
from app.models.request import Request
from app.models.request_item import RequestItem
from tests.conftest import AuthUser, auth_header, delete_request, login_token

OLD_CODE = 19101
NEW_CODE = 19104
CLIENT_NAME = "Тест логистика LOG-006"
PRODUCT_CODES = [OLD_CODE, NEW_CODE]


@pytest.fixture
async def related_catalog(catalog: dict[str, int], test_user: AuthUser):
    request_id = uuid4()
    warehouse_code = catalog["warehouse_code"]
    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(AvailableBalance).where(
                AvailableBalance.product_code.in_(PRODUCT_CODES)
            )
        )
        await session.execute(
            delete(Normative).where(Normative.product_code.in_(PRODUCT_CODES))
        )
        leftover_ids = (
            await session.scalars(
                select(Request.id).where(Request.client_name == CLIENT_NAME)
            )
        ).all()
        await session.execute(
            delete(RequestItem).where(
                RequestItem.product_code.in_(PRODUCT_CODES)
                | RequestItem.request_id.in_(leftover_ids or [uuid4()])
            )
        )
        if leftover_ids:
            await session.execute(delete(Request).where(Request.id.in_(leftover_ids)))
        await session.execute(delete(Product).where(Product.code.in_(PRODUCT_CODES)))
        await session.commit()

    async with AsyncSessionLocal() as session:
        session.add(
            Product(
                code=OLD_CODE,
                name="Подшипник устаревший",
                category="A",
                plant_id=catalog["plant_code"],
                weight_kg=Decimal("0.2500"),
                is_active=False,
                parent_code=None,
                children_code=NEW_CODE,
            )
        )
        session.add(
            Product(
                code=NEW_CODE,
                name="Подшипник актуальный",
                category="A",
                plant_id=catalog["plant_code"],
                weight_kg=Decimal("0.2500"),
                is_active=True,
                parent_code=OLD_CODE,
                children_code=None,
            )
        )
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
                product_code=NEW_CODE,
                warehouse_code=warehouse_code,
                quantity=Decimal("1000"),
                unit="шт",
                client_name=CLIENT_NAME,
                expiry_date=date(2026, 12, 31),
                category="A",
            )
        )
        session.add(
            AvailableBalance(
                warehouse_code=warehouse_code,
                product_code=NEW_CODE,
                available=Decimal("100"),
                plan=Decimal("100"),
                unit="шт",
                source="manual",
            )
        )
        session.add(
            AvailableBalance(
                warehouse_code=warehouse_code,
                product_code=OLD_CODE,
                available=Decimal("600"),
                plan=Decimal("600"),
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
                AvailableBalance.product_code.in_(PRODUCT_CODES)
            )
        )
        await session.commit()
    await delete_request(request_id)
    async with AsyncSessionLocal() as session:
        await session.execute(delete(Product).where(Product.code.in_(PRODUCT_CODES)))
        await session.commit()


def _warehouse(data: list[dict], warehouse_code: int) -> dict:
    return next(item for item in data if item["warehouse_code"] == warehouse_code)


def _item(warehouse: dict, product_code: int) -> dict:
    return next(
        item
        for item in warehouse["deficit_items"]
        if item["product_code"] == product_code
    )


async def test_related_group_uses_family_plan_and_orders_main(
    client: AsyncClient,
    logistics_user: AuthUser,
    related_catalog: dict,
) -> None:
    token = await login_token(client, logistics_user)
    warehouse_code = related_catalog["warehouse_code"]
    response = await client.get(
        "/api/v1/logistics/normative/dashboard",
        params={"warehouse_code": warehouse_code, "filter_mode": "all"},
        headers=auth_header(token),
    )
    assert response.status_code == 200, response.text
    warehouse = _warehouse(response.json()["data"], warehouse_code)
    codes = [item["product_code"] for item in warehouse["deficit_items"]]
    assert codes.index(NEW_CODE) < codes.index(OLD_CODE)

    main = _item(warehouse, NEW_CODE)
    related = _item(warehouse, OLD_CODE)
    assert main["is_group_main"] is True
    assert main["hide_group_metrics"] is False
    assert main["group_key"] == str(NEW_CODE)
    assert main["normative_quantity"] == 1000
    assert main["requirement"] == 1000
    assert main["available"] == 100
    assert main["plan"] == 100
    assert main["deficit"] == 300
    assert main["status"] == "warning"
    assert main["parent_code"] == OLD_CODE
    assert main["children_code"] is None
    assert main["is_active"] is True

    assert related["is_group_main"] is False
    assert related["hide_group_metrics"] is True
    assert related["group_key"] == str(NEW_CODE)
    assert related["group_index"] == main["group_index"]
    assert related["normative_quantity"] == 0
    assert related["requirement"] == 0
    assert related["deficit"] == 0
    assert related["available"] == 600
    assert related["plan"] == 600
    assert related["is_active"] is False
    assert related["children_code"] == NEW_CODE
    assert codes[codes.index(NEW_CODE) + 1] == OLD_CODE

    deficit_only = await client.get(
        "/api/v1/logistics/normative/dashboard",
        params={"warehouse_code": warehouse_code, "filter_mode": "deficit_only"},
        headers=auth_header(token),
    )
    assert deficit_only.status_code == 200, deficit_only.text
    grouped = _warehouse(deficit_only.json()["data"], warehouse_code)
    grouped_codes = {item["product_code"] for item in grouped["deficit_items"]}
    assert NEW_CODE in grouped_codes
    assert OLD_CODE in grouped_codes
    grouped_main = _item(grouped, NEW_CODE)
    grouped_related = _item(grouped, OLD_CODE)
    assert grouped_main["deficit"] == 300
    assert grouped_related["hide_group_metrics"] is True

    orders = await client.post(
        f"/api/v1/logistics/normative/{warehouse_code}/generate-orders",
        headers=auth_header(token),
    )
    assert orders.status_code == 200, orders.text
    items = [
        item
        for order in orders.json()["data"]["orders"]
        for item in order["items"]
        if item["product_code"] in PRODUCT_CODES
    ]
    assert len(items) == 1
    assert items[0]["product_code"] == NEW_CODE
    assert items[0]["deficit"] == 300


async def test_generate_orders_by_old_code_still_orders_main(
    client: AsyncClient,
    logistics_user: AuthUser,
    related_catalog: dict,
) -> None:
    token = await login_token(client, logistics_user)
    warehouse_code = related_catalog["warehouse_code"]
    response = await client.post(
        f"/api/v1/logistics/normative/{warehouse_code}/generate-orders",
        json={"product_codes": [OLD_CODE]},
        headers=auth_header(token),
    )
    assert response.status_code == 200, response.text
    items = [
        item
        for order in response.json()["data"]["orders"]
        for item in order["items"]
        if item["product_code"] in PRODUCT_CODES
    ]
    assert len(items) == 1
    assert items[0]["product_code"] == NEW_CODE
    assert items[0]["deficit"] == 300
