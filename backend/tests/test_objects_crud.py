from decimal import Decimal

from httpx import AsyncClient
from sqlalchemy import delete

from app.core.database import AsyncSessionLocal
from app.models.available_balance import AvailableBalance
from app.models.object import Object
from app.models.product import Product
from tests.conftest import AuthUser, auth_header, login_token

NEW_CODE = 3001
NEW_PLANT_CODE = 3006
DELETE_OK_CODE = 3003
DELETE_BLOCKED_WAREHOUSE = 3004
DELETE_BLOCKED_PLANT = 3005
DUPLICATE_ERP_CODE = 3002


async def _cleanup_admin_objects() -> None:
    codes = [
        NEW_CODE,
        NEW_PLANT_CODE,
        DELETE_OK_CODE,
        DELETE_BLOCKED_WAREHOUSE,
        DELETE_BLOCKED_PLANT,
        18210,
        DUPLICATE_ERP_CODE,
    ]
    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(AvailableBalance).where(AvailableBalance.warehouse_code.in_(codes))
        )
        await session.execute(delete(Product).where(Product.code == 18210))
        await session.execute(delete(Object).where(Object.code.in_(codes)))
        await session.commit()


async def _seed_object(code: int, **kwargs: object) -> None:
    async with AsyncSessionLocal() as session:
        session.add(
            Object(
                code=code,
                name=str(kwargs.get("name", f"Объект {code}")),
                city=str(kwargs.get("city", "Москва")),
                region=kwargs.get("region"),  # type: ignore[arg-type]
                address=kwargs.get("address"),  # type: ignore[arg-type]
                type=str(kwargs.get("type", "warehouse")),
                is_active=bool(kwargs.get("is_active", True)),
            )
        )
        await session.commit()


async def test_guest_can_list_objects(
    client: AsyncClient, guest_user: AuthUser, catalog: dict[str, int]
) -> None:
    token = await login_token(client, guest_user)
    response = await client.get(
        "/api/v1/references/objects",
        headers=auth_header(token),
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]


async def test_create_forbidden_for_non_logistics(
    client: AsyncClient,
    test_user: AuthUser,
    pp_user: AuthUser,
    economist_user: AuthUser,
    guest_user: AuthUser,
    catalog: dict[str, int],
) -> None:
    payload = {
        "code": NEW_CODE,
        "name": "Склад Тестовый",
        "city": "Москва",
        "type": "warehouse",
    }
    for user in (test_user, pp_user, economist_user, guest_user):
        token = await login_token(client, user)
        response = await client.post(
            "/api/v1/references/objects",
            headers=auth_header(token),
            json=payload,
        )
        assert response.status_code == 403, response.text


async def test_create_get_update_delete_object(
    client: AsyncClient, logistics_user: AuthUser, catalog: dict[str, int]
) -> None:
    await _cleanup_admin_objects()
    token = await login_token(client, logistics_user)
    try:
        created = await client.post(
            "/api/v1/references/objects",
            headers=auth_header(token),
            json={
                "code": NEW_CODE,
                "name": "Склад Тестовый",
                "city": "Москва",
                "type": "warehouse",
                "erp_warehouse_code": "T001",
                "loading_point": "2T01",
            },
        )
        assert created.status_code == 200, created.text
        created_data = created.json()["data"]
        assert created_data["code"] == NEW_CODE
        assert created_data["name"] == "Склад Тестовый"
        assert created_data["city"] == "Москва"
        assert created_data["type"] == "warehouse"
        assert created_data["erp_warehouse_code"] == "T001"
        assert created_data["erp_plant_code"] is None
        assert created_data["loading_point"] == "2T01"
        assert created_data["is_active"] is True
        assert created_data["last_modified_by"]["id"] == str(logistics_user.id)
        assert created_data["last_modified_at"] is not None

        duplicate = await client.post(
            "/api/v1/references/objects",
            headers=auth_header(token),
            json={
                "code": NEW_CODE,
                "name": "Другой склад",
                "city": "Казань",
                "type": "warehouse",
                "erp_warehouse_code": "T002",
            },
        )
        assert duplicate.status_code == 409
        assert duplicate.json()["error"]["code"] == "ALREADY_EXISTS"

        edit = await client.get(
            f"/api/v1/references/objects/{NEW_CODE}/edit",
            headers=auth_header(token),
        )
        assert edit.status_code == 200, edit.text
        assert edit.json()["data"]["name"] == "Склад Тестовый"
        assert edit.json()["data"]["erp_warehouse_code"] == "T001"
        assert edit.json()["data"]["loading_point"] == "2T01"

        updated = await client.put(
            f"/api/v1/references/objects/{NEW_CODE}",
            headers=auth_header(token),
            json={
                "name": "Склад Тестовый (обновлён)",
                "city": "Санкт-Петербург",
                "erp_warehouse_code": "T009",
                "loading_point": "2T09",
            },
        )
        assert updated.status_code == 200, updated.text
        data = updated.json()["data"]
        assert data["name"] == "Склад Тестовый (обновлён)"
        assert data["city"] == "Санкт-Петербург"
        assert data["type"] == "warehouse"
        assert data["erp_warehouse_code"] == "T009"
        assert data["loading_point"] == "2T09"
        assert data["last_modified_by"]["full_name"] == logistics_user.full_name

        deleted = await client.delete(
            f"/api/v1/references/objects/{NEW_CODE}",
            headers=auth_header(token),
        )
        assert deleted.status_code == 200
        assert deleted.json()["message"] == "Объект удален"

        missing = await client.get(
            f"/api/v1/references/objects/{NEW_CODE}",
            headers=auth_header(token),
        )
        assert missing.status_code == 404
    finally:
        await _cleanup_admin_objects()


async def test_create_validation(
    client: AsyncClient, logistics_user: AuthUser, catalog: dict[str, int]
) -> None:
    token = await login_token(client, logistics_user)
    invalid_type = await client.post(
        "/api/v1/references/objects",
        headers=auth_header(token),
        json={
            "code": 3999,
            "name": "Неверный тип",
            "city": "Москва",
            "type": "office",
        },
    )
    assert invalid_type.status_code == 422

    invalid_code = await client.post(
        "/api/v1/references/objects",
        headers=auth_header(token),
        json={
            "code": 0,
            "name": "Нулевой код",
            "city": "Москва",
            "type": "warehouse",
        },
    )
    assert invalid_code.status_code == 422

    empty_name = await client.post(
        "/api/v1/references/objects",
        headers=auth_header(token),
        json={
            "code": 3998,
            "name": "   ",
            "city": "Москва",
            "type": "warehouse",
        },
    )
    assert empty_name.status_code == 422


async def test_create_erp_validation(
    client: AsyncClient, logistics_user: AuthUser, catalog: dict[str, int]
) -> None:
    await _cleanup_admin_objects()
    token = await login_token(client, logistics_user)
    try:
        missing_warehouse = await client.post(
            "/api/v1/references/objects",
            headers=auth_header(token),
            json={
                "code": NEW_CODE,
                "name": "Склад без ERP",
                "city": "Москва",
                "type": "warehouse",
            },
        )
        assert missing_warehouse.status_code == 400
        assert missing_warehouse.json()["error"]["code"] == "VALIDATION_ERROR"

        missing_plant = await client.post(
            "/api/v1/references/objects",
            headers=auth_header(token),
            json={
                "code": NEW_PLANT_CODE,
                "name": "Завод без ERP",
                "city": "Москва",
                "type": "plant",
            },
        )
        assert missing_plant.status_code == 400

        invalid_plant = await client.post(
            "/api/v1/references/objects",
            headers=auth_header(token),
            json={
                "code": NEW_PLANT_CODE,
                "name": "Завод короткий код",
                "city": "Москва",
                "type": "plant",
                "erp_plant_code": 99,
            },
        )
        assert invalid_plant.status_code == 400

        invalid_warehouse = await client.post(
            "/api/v1/references/objects",
            headers=auth_header(token),
            json={
                "code": NEW_CODE,
                "name": "Склад короткий код",
                "city": "Москва",
                "type": "warehouse",
                "erp_warehouse_code": "AB",
            },
        )
        assert invalid_warehouse.status_code == 400

        invalid_loading = await client.post(
            "/api/v1/references/objects",
            headers=auth_header(token),
            json={
                "code": NEW_CODE,
                "name": "Склад пункт",
                "city": "Москва",
                "type": "warehouse",
                "erp_warehouse_code": "T001",
                "loading_point": "12",
            },
        )
        assert invalid_loading.status_code == 400
    finally:
        await _cleanup_admin_objects()


async def test_erp_codes_are_unique(
    client: AsyncClient, logistics_user: AuthUser, catalog: dict[str, int]
) -> None:
    await _cleanup_admin_objects()
    token = await login_token(client, logistics_user)
    try:
        first = await client.post(
            "/api/v1/references/objects",
            headers=auth_header(token),
            json={
                "code": NEW_PLANT_CODE,
                "name": "Завод Тестовый",
                "city": "Москва",
                "type": "plant",
                "erp_plant_code": 2499,
                "loading_point": "2R05",
            },
        )
        assert first.status_code == 200, first.text
        assert first.json()["data"]["erp_plant_code"] == 2499

        duplicate = await client.post(
            "/api/v1/references/objects",
            headers=auth_header(token),
            json={
                "code": DUPLICATE_ERP_CODE,
                "name": "Завод Дубль",
                "city": "Москва",
                "type": "plant",
                "erp_plant_code": 2499,
            },
        )
        assert duplicate.status_code == 409, duplicate.text
        assert duplicate.json()["error"]["code"] == "CONFLICT"

        warehouse = await client.post(
            "/api/v1/references/objects",
            headers=auth_header(token),
            json={
                "code": NEW_CODE,
                "name": "Склад Тестовый",
                "city": "Москва",
                "type": "warehouse",
                "erp_warehouse_code": "t001",
            },
        )
        assert warehouse.status_code == 200, warehouse.text
        assert warehouse.json()["data"]["erp_warehouse_code"] == "T001"

        duplicate_wh = await client.post(
            "/api/v1/references/objects",
            headers=auth_header(token),
            json={
                "code": DUPLICATE_ERP_CODE,
                "name": "Склад Дубль",
                "city": "Москва",
                "type": "warehouse",
                "erp_warehouse_code": "T001",
            },
        )
        assert duplicate_wh.status_code == 409
        assert duplicate_wh.json()["error"]["code"] == "CONFLICT"
    finally:
        await _cleanup_admin_objects()


async def test_edit_forbidden_for_pp(
    client: AsyncClient, pp_user: AuthUser, catalog: dict[str, int]
) -> None:
    token = await login_token(client, pp_user)
    response = await client.get(
        f"/api/v1/references/objects/{catalog['warehouse_code']}/edit",
        headers=auth_header(token),
    )
    assert response.status_code == 403


async def test_delete_blocked_by_relations(
    client: AsyncClient, logistics_user: AuthUser, catalog: dict[str, int]
) -> None:
    await _cleanup_admin_objects()
    await _seed_object(DELETE_BLOCKED_WAREHOUSE, type="warehouse")
    await _seed_object(DELETE_BLOCKED_PLANT, type="plant", name="Завод тестовый")
    async with AsyncSessionLocal() as session:
        session.add(
            AvailableBalance(
                warehouse_code=DELETE_BLOCKED_WAREHOUSE,
                product_code=catalog["product_code"],
                available=Decimal("10"),
                plan=Decimal("10"),
                unit="шт",
            )
        )
        session.add(
            Product(
                code=18210,
                name="Продукт для блокировки завода",
                category="A",
                plant_id=DELETE_BLOCKED_PLANT,
                weight_kg=Decimal("0.2500"),
                is_active=True,
            )
        )
        await session.commit()

    token = await login_token(client, logistics_user)
    try:
        blocked_wh = await client.delete(
            f"/api/v1/references/objects/{DELETE_BLOCKED_WAREHOUSE}",
            headers=auth_header(token),
        )
        assert blocked_wh.status_code == 409
        assert blocked_wh.json()["error"]["code"] == "HAS_RELATIONS"

        blocked_plant = await client.delete(
            f"/api/v1/references/objects/{DELETE_BLOCKED_PLANT}",
            headers=auth_header(token),
        )
        assert blocked_plant.status_code == 409
        assert blocked_plant.json()["error"]["code"] == "HAS_RELATIONS"

        await _seed_object(DELETE_OK_CODE, type="warehouse", name="Склад без связей")
        deleted = await client.delete(
            f"/api/v1/references/objects/{DELETE_OK_CODE}",
            headers=auth_header(token),
        )
        assert deleted.status_code == 200
    finally:
        await _cleanup_admin_objects()


async def test_commercial_cannot_update_or_delete(
    client: AsyncClient, test_user: AuthUser, catalog: dict[str, int]
) -> None:
    token = await login_token(client, test_user)
    updated = await client.put(
        f"/api/v1/references/objects/{catalog['warehouse_code']}",
        headers=auth_header(token),
        json={"name": "Хак"},
    )
    assert updated.status_code == 403
    deleted = await client.delete(
        f"/api/v1/references/objects/{catalog['warehouse_code']}",
        headers=auth_header(token),
    )
    assert deleted.status_code == 403
