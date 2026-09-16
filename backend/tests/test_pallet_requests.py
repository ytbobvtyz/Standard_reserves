from decimal import Decimal

from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.params import Params
from app.models.product import Product
from tests.conftest import AuthUser, auth_header, delete_request, login_token
from tests.test_approvals import _create_submitted
from tests.test_requests import _create


async def _set_pallet_mode(
    *,
    enabled: bool,
    product_code: int,
    pallet_qty: int | None,
    weight_kg: Decimal | None = None,
) -> None:
    async with AsyncSessionLocal() as session:
        params = await session.get(Params, 1)
        assert params is not None
        params.pallet_multiple = enabled
        product = await session.get(Product, product_code)
        assert product is not None
        product.pallet_qty = pallet_qty
        if weight_kg is not None:
            product.weight_kg = weight_kg
        await session.commit()


async def test_create_rounds_up_when_pallet_multiple_enabled(
    client: AsyncClient, test_user: AuthUser, catalog: dict[str, int]
) -> None:
    await _set_pallet_mode(
        enabled=True, product_code=catalog["product_code"], pallet_qty=48
    )
    token = await login_token(client, test_user)
    status, body = await _create(
        client,
        token,
        items=[
            {
                "product_code": catalog["product_code"],
                "warehouse_code": catalog["warehouse_code"],
                "quantity_requested": 10,
                "unit": "шт",
            }
        ],
    )
    assert status == 201, body
    item = body["data"]["items"][0]
    assert Decimal(str(item["quantity_requested"])) == Decimal("48")
    assert Decimal(str(item["requirement"])) == Decimal("48")
    await delete_request(body["data"]["id"])


async def test_create_keeps_qty_when_pallet_multiple_disabled(
    client: AsyncClient, test_user: AuthUser, catalog: dict[str, int]
) -> None:
    await _set_pallet_mode(
        enabled=False, product_code=catalog["product_code"], pallet_qty=48
    )
    token = await login_token(client, test_user)
    status, body = await _create(
        client,
        token,
        items=[
            {
                "product_code": catalog["product_code"],
                "warehouse_code": catalog["warehouse_code"],
                "quantity_requested": 10,
                "unit": "шт",
            }
        ],
    )
    assert status == 201, body
    item = body["data"]["items"][0]
    assert Decimal(str(item["quantity_requested"])) == Decimal("10")
    await delete_request(body["data"]["id"])


async def test_create_uses_one_piece_when_pallet_qty_missing(
    client: AsyncClient, test_user: AuthUser, catalog: dict[str, int]
) -> None:
    await _set_pallet_mode(
        enabled=True, product_code=catalog["product_code"], pallet_qty=None
    )
    token = await login_token(client, test_user)
    status, body = await _create(
        client,
        token,
        items=[
            {
                "product_code": catalog["product_code"],
                "warehouse_code": catalog["warehouse_code"],
                "quantity_requested": 10.1,
                "unit": "шт",
            }
        ],
    )
    assert status == 201, body
    item = body["data"]["items"][0]
    assert Decimal(str(item["quantity_requested"])) == Decimal("11")
    await delete_request(body["data"]["id"])


async def test_update_draft_rounds_when_pallet_multiple_enabled(
    client: AsyncClient, test_user: AuthUser, catalog: dict[str, int]
) -> None:
    await _set_pallet_mode(
        enabled=True, product_code=catalog["product_code"], pallet_qty=48
    )
    token = await login_token(client, test_user)
    _, created = await _create(client, token)
    request_id = created["data"]["id"]
    response = await client.put(
        f"/api/v1/requests/{request_id}",
        headers=auth_header(token),
        json={
            "items": [
                {
                    "product_code": catalog["product_code"],
                    "warehouse_code": catalog["warehouse_code"],
                    "quantity_requested": 10,
                    "unit": "шт",
                }
            ]
        },
    )
    assert response.status_code == 200, response.text
    detail = await client.get(
        f"/api/v1/requests/{request_id}",
        headers=auth_header(token),
    )
    item = detail.json()["data"]["items"][0]
    assert Decimal(str(item["quantity_requested"])) == Decimal("48")
    await delete_request(request_id)


async def test_approver_can_set_any_quantity_when_pallet_multiple_enabled(
    client: AsyncClient,
    test_user: AuthUser,
    pp_user: AuthUser,
    catalog: dict[str, int],
) -> None:
    await _set_pallet_mode(
        enabled=True, product_code=catalog["product_code"], pallet_qty=48
    )
    commercial_token = await login_token(client, test_user)
    pp_token = await login_token(client, pp_user)
    request_id = await _create_submitted(
        client,
        commercial_token,
        items=[
            {
                "product_code": catalog["product_code"],
                "warehouse_code": catalog["warehouse_code"],
                "quantity_requested": 48,
                "unit": "шт",
            }
        ],
    )
    response = await client.post(
        f"/api/v1/approvals/pp/{request_id}/action",
        headers=auth_header(pp_token),
        json={
            "action": "approve",
            "items": [
                {
                    "product_code": catalog["product_code"],
                    "warehouse_code": catalog["warehouse_code"],
                    "quantity_approved": 10,
                }
            ],
            "comment": "Согласовано не кратно поддону",
        },
    )
    assert response.status_code == 200, response.text
    detail = await client.get(
        f"/api/v1/requests/{request_id}",
        headers=auth_header(pp_token),
    )
    item = detail.json()["data"]["items"][0]
    assert Decimal(str(item["quantity_requested"])) == Decimal("48")
    assert Decimal(str(item["quantity_approved"])) == Decimal("10")
    await delete_request(request_id)


async def test_create_rounds_tons_via_weight_and_pallet_qty(
    client: AsyncClient, test_user: AuthUser, catalog: dict[str, int]
) -> None:
    await _set_pallet_mode(
        enabled=True,
        product_code=catalog["product_code"],
        pallet_qty=756,
        weight_kg=Decimal("0.82"),
    )
    token = await login_token(client, test_user)
    status, body = await _create(
        client,
        token,
        items=[
            {
                "product_code": catalog["product_code"],
                "warehouse_code": catalog["warehouse_code"],
                "quantity_requested": 1,
                "unit": "т",
            }
        ],
    )
    assert status == 201, body
    item = body["data"]["items"][0]
    assert Decimal(str(item["quantity_requested"])) == Decimal("1.23984")
    await delete_request(body["data"]["id"])
