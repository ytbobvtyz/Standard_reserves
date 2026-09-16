from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO
from uuid import UUID

import pytest
from httpx import AsyncClient
from openpyxl import Workbook, load_workbook
from sqlalchemy import func, select

from app.core.database import AsyncSessionLocal
from app.models.normative import Normative
from app.models.object import Object
from app.models.product import Product
from app.models.production_request import ProductionRequest, ProductionRequestItem
from app.services.production_requests import _parse_quantity
from tests.conftest import AuthUser, auth_header, login_token


def _xlsx(rows: list[list[object]]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(
        [
            "Завод ERP",
            "Склад ERP",
            "Артикул",
            "Количество",
            "Ед.",
            "Клиент",
        ]
    )
    for row in rows:
        sheet.append(row)
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


async def test_production_request_template_starts_with_erp_columns(
    client: AsyncClient,
    logistics_user: AuthUser,
    catalog: dict[str, int],
) -> None:
    token = await login_token(client, logistics_user)
    response = await client.get(
        "/api/v1/production-requests/template",
        headers=auth_header(token),
    )
    assert response.status_code == 200, response.text
    workbook = load_workbook(BytesIO(response.content), data_only=True)
    headers = [cell.value for cell in workbook.active[1]]
    assert headers[:3] == ["Завод ERP", "Склад ERP", "Артикул"]


async def test_upload_update_and_delete_production_request_batch(
    client: AsyncClient,
    logistics_user: AuthUser,
    catalog: dict[str, int],
) -> None:
    token = await login_token(client, logistics_user)
    valid_from = date.today() - timedelta(days=30)
    valid_to = date.today() + timedelta(days=90)
    content = _xlsx(
        [
            [
                catalog["erp_plant_code"],
                catalog["erp_warehouse_code"],
                catalog["product_code"],
                1000,
                "шт",
                "Клиент строки",
            ],
            [
                catalog["erp_plant_code_2"],
                catalog["erp_warehouse_code_2"],
                catalog["product_code_2"],
                500,
                "кг",
                None,
            ],
            [
                catalog["erp_plant_code"],
                catalog["erp_warehouse_code"],
                99999999,
                100,
                "шт",
                None,
            ],
            [
                catalog["erp_plant_code"],
                catalog["erp_warehouse_code"],
                catalog["product_code"],
                "не число",
                "шт",
                None,
            ],
        ]
    )
    response = await client.post(
        "/api/v1/production-requests/upload",
        headers=auth_header(token),
        files={
            "file": (
                "normatives.xlsx",
                content,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        data={
            "client_name": "Общий клиент",
            "valid_from": valid_from.isoformat(),
            "valid_to": valid_to.isoformat(),
        },
    )
    assert response.status_code == 201, response.text
    result = response.json()["data"]
    assert result["imported_count"] == 2
    assert result["total_rows"] == 4
    assert result["error_count"] == 2
    assert result["message"] == "Загружено 2 строк из 4"
    assert [item["row"] for item in result["error_details"]] == [4, 5]
    assert "артикул 99999999 не найден" in result["error_details"][0]["message"]
    assert "ожидается число" in result["error_details"][1]["message"]
    batch = result["production_request"]
    assert batch["source"] == "excel_upload"
    assert batch["items_count"] == 2
    assert batch["client_name"] == "Общий клиент"
    batch_id = UUID(batch["id"])

    try:
        async with AsyncSessionLocal() as session:
            items = (
                await session.scalars(
                    select(ProductionRequestItem).where(
                        ProductionRequestItem.production_request_id == batch_id
                    )
                )
            ).all()
            assert len(items) == 2
            item_ids = [item.id for item in items]
            normatives = (
                await session.scalars(
                    select(Normative).where(
                        Normative.production_request_item_id.in_(item_ids)
                    )
                )
            ).all()
            assert len(normatives) == 2
            assert all(item.request_id is None for item in normatives)
            assert {item.client_name for item in normatives} == {
                "Клиент строки",
                "Общий клиент",
            }
            assert {item.unit for item in normatives} == {"шт", "кг"}

        listing = await client.get(
            "/api/v1/production-requests",
            headers=auth_header(token),
        )
        assert listing.status_code == 200, listing.text
        listed_ids = {item["id"] for item in listing.json()["data"]}
        assert str(batch_id) in listed_ids

        new_from = date.today() - timedelta(days=60)
        new_to = date.today() + timedelta(days=180)
        updated = await client.patch(
            f"/api/v1/production-requests/{batch_id}/dates",
            headers=auth_header(token),
            json={
                "valid_from": new_from.isoformat(),
                "valid_to": new_to.isoformat(),
            },
        )
        assert updated.status_code == 200, updated.text
        assert updated.json()["data"]["valid_from"] == new_from.isoformat()
        assert updated.json()["data"]["valid_to"] == new_to.isoformat()

        async with AsyncSessionLocal() as session:
            expiries = (
                await session.scalars(
                    select(Normative.expiry_date).where(
                        Normative.production_request_item_id.in_(item_ids)
                    )
                )
            ).all()
            assert expiries == [new_to, new_to]

        deleted = await client.delete(
            f"/api/v1/production-requests/{batch_id}",
            headers=auth_header(token),
        )
        assert deleted.status_code == 200, deleted.text

        async with AsyncSessionLocal() as session:
            assert await session.get(ProductionRequest, batch_id) is None
            items_count = await session.scalar(
                select(func.count())
                .select_from(ProductionRequestItem)
                .where(ProductionRequestItem.production_request_id == batch_id)
            )
            normatives_count = await session.scalar(
                select(func.count())
                .select_from(Normative)
                .where(Normative.production_request_item_id.in_(item_ids))
            )
            assert items_count == 0
            assert normatives_count == 0
    finally:
        async with AsyncSessionLocal() as session:
            remaining = await session.get(ProductionRequest, batch_id)
            if remaining is not None:
                await session.delete(remaining)
                await session.commit()


async def test_commercial_cannot_manage_production_requests(
    client: AsyncClient,
    test_user: AuthUser,
    catalog: dict[str, int],
) -> None:
    token = await login_token(client, test_user)
    response = await client.get(
        "/api/v1/production-requests",
        headers=auth_header(token),
    )
    assert response.status_code == 403


async def test_economist_and_planner_can_list_production_requests(
    client: AsyncClient,
    economist_user: AuthUser,
    pp_user: AuthUser,
    catalog: dict[str, int],
) -> None:
    for user in (economist_user, pp_user):
        token = await login_token(client, user)
        response = await client.get(
            "/api/v1/production-requests",
            headers=auth_header(token),
        )
        assert response.status_code == 200, response.text


async def test_upload_accepts_erp_plant_code_on_warehouse_only(
    client: AsyncClient,
    logistics_user: AuthUser,
    catalog: dict[str, int],
) -> None:
    """LogLab-style data: 2401 lives on warehouses, not on a type=plant row."""
    token = await login_token(client, logistics_user)
    warehouse_code = catalog["warehouse_code"]
    erp_plant_only_on_warehouse = 2410
    previous_plant_code = None
    async with AsyncSessionLocal() as session:
        warehouse = await session.get(Object, warehouse_code)
        assert warehouse is not None
        previous_plant_code = warehouse.erp_plant_code
        warehouse.erp_plant_code = erp_plant_only_on_warehouse
        await session.commit()

    batch_id: UUID | None = None
    try:
        valid_from = date.today() - timedelta(days=30)
        valid_to = date.today() + timedelta(days=90)
        content = _xlsx(
            [
                [
                    erp_plant_only_on_warehouse,
                    catalog["erp_warehouse_code"],
                    catalog["product_code"],
                    1000,
                    "шт",
                    "Клиент ERP на складе",
                ]
            ]
        )
        response = await client.post(
            "/api/v1/production-requests/upload",
            headers=auth_header(token),
            files={
                "file": (
                    "normatives.xlsx",
                    content,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
            data={
                "valid_from": valid_from.isoformat(),
                "valid_to": valid_to.isoformat(),
            },
        )
        assert response.status_code == 201, response.text
        result = response.json()["data"]
        assert result["imported_count"] == 1
        assert result["total_rows"] == 1
        assert result["error_count"] == 0
        assert result["error_details"] == []
        batch_id = UUID(result["production_request"]["id"])
    finally:
        async with AsyncSessionLocal() as session:
            warehouse = await session.get(Object, warehouse_code)
            if warehouse is not None:
                warehouse.erp_plant_code = previous_plant_code
            if batch_id is not None:
                remaining = await session.get(ProductionRequest, batch_id)
                if remaining is not None:
                    await session.delete(remaining)
            await session.commit()


async def test_upload_without_client_creates_batch(
    client: AsyncClient,
    logistics_user: AuthUser,
    catalog: dict[str, int],
) -> None:
    token = await login_token(client, logistics_user)
    valid_from = date.today() - timedelta(days=30)
    valid_to = date.today() + timedelta(days=90)
    content = _xlsx(
        [
            [
                catalog["erp_plant_code"],
                catalog["erp_warehouse_code"],
                catalog["product_code"],
                250,
                "шт",
                None,
            ]
        ]
    )
    batch_id: UUID | None = None
    try:
        response = await client.post(
            "/api/v1/production-requests/upload",
            headers=auth_header(token),
            files={
                "file": (
                    "normatives.xlsx",
                    content,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
            data={
                "valid_from": valid_from.isoformat(),
                "valid_to": valid_to.isoformat(),
            },
        )
        assert response.status_code == 201, response.text
        result = response.json()["data"]
        assert result["imported_count"] == 1
        assert result["error_count"] == 0
        assert result["production_request"]["client_name"] is None
        assert result["production_request"]["items"][0]["client_name"] == ""
        batch_id = UUID(result["production_request"]["id"])
    finally:
        async with AsyncSessionLocal() as session:
            if batch_id is not None:
                remaining = await session.get(ProductionRequest, batch_id)
                if remaining is not None:
                    await session.delete(remaining)
                    await session.commit()


async def test_preview_and_upload_inactive_articles(
    client: AsyncClient,
    logistics_user: AuthUser,
    catalog: dict[str, int],
) -> None:
    token = await login_token(client, logistics_user)
    product_code = catalog["product_code"]
    async with AsyncSessionLocal() as session:
        product = await session.get(Product, product_code)
        assert product is not None
        product.is_active = False
        await session.commit()

    content = _xlsx(
        [
            [
                catalog["erp_plant_code"],
                catalog["erp_warehouse_code"],
                product_code,
                100,
                "шт",
                "Исторический клиент",
            ]
        ]
    )
    batch_id: UUID | None = None
    try:
        preview = await client.post(
            "/api/v1/production-requests/preview",
            headers=auth_header(token),
            files={
                "file": (
                    "normatives.xlsx",
                    content,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )
        assert preview.status_code == 200, preview.text
        preview_data = preview.json()["data"]
        assert preview_data["total_rows"] == 1
        assert [item["code"] for item in preview_data["inactive_products"]] == [
            product_code
        ]

        skipped = await client.post(
            "/api/v1/production-requests/upload",
            headers=auth_header(token),
            files={
                "file": (
                    "normatives.xlsx",
                    content,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
            data={
                "valid_from": date.today().isoformat(),
                "valid_to": (date.today() + timedelta(days=30)).isoformat(),
                "inactive_policy": "active_only",
            },
        )
        assert skipped.status_code == 201, skipped.text
        skipped_data = skipped.json()["data"]
        assert skipped_data["imported_count"] == 0
        assert skipped_data["production_request"] is None
        assert "неактивен" in skipped_data["error_details"][0]["message"]

        included = await client.post(
            "/api/v1/production-requests/upload",
            headers=auth_header(token),
            files={
                "file": (
                    "normatives.xlsx",
                    content,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
            data={
                "valid_from": date.today().isoformat(),
                "valid_to": (date.today() + timedelta(days=30)).isoformat(),
                "inactive_policy": "include_inactive",
            },
        )
        assert included.status_code == 201, included.text
        included_data = included.json()["data"]
        assert included_data["imported_count"] == 1
        batch_id = UUID(included_data["production_request"]["id"])
        async with AsyncSessionLocal() as session:
            product = await session.get(Product, product_code)
            assert product is not None
            assert product.is_active is False
    finally:
        async with AsyncSessionLocal() as session:
            product = await session.get(Product, product_code)
            if product is not None:
                product.is_active = True
            if batch_id is not None:
                remaining = await session.get(ProductionRequest, batch_id)
                if remaining is not None:
                    await session.delete(remaining)
            await session.commit()


def test_parse_quantity_keeps_small_tons() -> None:
    assert _parse_quantity("0.004", "т") == Decimal("0.004000")


def test_parse_quantity_rejects_tons_that_round_to_zero() -> None:
    with pytest.raises(ValueError, match="после округления равно нулю"):
        _parse_quantity("0.0000004", "т")


async def test_upload_keeps_fractional_tons(
    client: AsyncClient,
    logistics_user: AuthUser,
    catalog: dict[str, int],
) -> None:
    token = await login_token(client, logistics_user)
    content = _xlsx(
        [
            [
                catalog["erp_plant_code"],
                catalog["erp_warehouse_code"],
                catalog["product_code"],
                0.004,
                "т",
                "Ретро",
            ]
        ]
    )
    response = await client.post(
        "/api/v1/production-requests/upload",
        headers=auth_header(token),
        files={
            "file": (
                "normatives.xlsx",
                content,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        data={
            "valid_from": date.today().isoformat(),
            "valid_to": (date.today() + timedelta(days=30)).isoformat(),
        },
    )
    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert data["imported_count"] == 1
    assert data["error_count"] == 0
    batch_id = UUID(data["production_request"]["id"])
    try:
        async with AsyncSessionLocal() as session:
            item = (
                await session.scalars(
                    select(ProductionRequestItem).where(
                        ProductionRequestItem.production_request_id == batch_id
                    )
                )
            ).one()
            assert item.unit == "т"
            assert item.quantity == Decimal("0.004000")
    finally:
        async with AsyncSessionLocal() as session:
            remaining = await session.get(ProductionRequest, batch_id)
            if remaining is not None:
                await session.delete(remaining)
                await session.commit()
