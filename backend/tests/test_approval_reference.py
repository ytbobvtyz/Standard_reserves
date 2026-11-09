from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import delete, event, select, text

from app.core.database import AsyncSessionLocal
from app.models.actual_shipment import ActualShipment
from app.models.normative import Normative
from app.models.object import Object
from app.models.product import Product
from app.models.request import Request
from app.services.approval_reference import ReferenceKey, load_item_references
from app.services.optimal_stock import previous_month_starts
from tests.conftest import (
    AuthUser,
    auth_header,
    delete_request,
    ensure_client,
    login_token,
)

PRODUCT = 91055
SYSTEM_PRODUCT = 91056
POINT_A = "A055"
POINT_B = "B055"


def _day(start: date) -> date:
    return start + timedelta(days=9)


def _assert_coverage(actual: dict, expected: dict) -> None:
    for key, value in expected.items():
        if value is None:
            assert actual[key] is None, key
            continue
        assert actual[key] == pytest.approx(value, abs=1e-9), key


async def _pin_loading_point(code: int, point: str) -> str | None:
    async with AsyncSessionLocal() as session:
        occupant = await session.scalar(
            select(Object).where(
                Object.loading_point == point,
                Object.code != code,
            )
        )
        if occupant is not None:
            occupant.loading_point = None
            await session.flush()
        target = await session.get(Object, code)
        assert target is not None
        previous = target.loading_point
        target.loading_point = point
        await session.commit()
        return previous


async def _restore_loading_point(code: int, previous: str | None) -> None:
    async with AsyncSessionLocal() as session:
        target = await session.get(Object, code)
        assert target is not None
        target.loading_point = previous
        await session.commit()


async def _ensure_product(code: int, name: str, weight: Decimal) -> None:
    async with AsyncSessionLocal() as session:
        existing = await session.get(Product, code)
        if existing is None:
            session.add(
                Product(
                    code=code,
                    name=name,
                    category="A",
                    plant_id=1001,
                    weight_kg=weight,
                    pallet_qty=100000,
                    is_active=True,
                )
            )
        else:
            existing.deleted_at = None
            existing.name = name
            existing.category = "A"
            existing.plant_id = 1001
            existing.weight_kg = weight
            existing.pallet_qty = 100000
            existing.is_active = True
        await session.commit()


async def _set_weight(code: int, weight: Decimal) -> None:
    async with AsyncSessionLocal() as session:
        product = await session.get(Product, code)
        assert product is not None
        product.weight_kg = weight
        await session.commit()


async def test_reference_batch_is_two_queries(db_ready: None) -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(text("SELECT 1"))
        count = {"n": 0}

        def bump(*_args, **_kwargs) -> None:
            count["n"] += 1

        bind = session.sync_session.bind
        assert bind is not None
        event.listen(bind, "before_cursor_execute", bump)
        try:
            assert await load_item_references(session, []) == {}
            assert count["n"] == 0
            keys = [
                ReferenceKey(uuid4(), PRODUCT, 2001, "т", Decimal("0.25")),
                ReferenceKey(uuid4(), PRODUCT, 2002, "шт", Decimal("0.25")),
                ReferenceKey(uuid4(), 10001, 2001, "т", Decimal("1")),
                ReferenceKey(uuid4(), 10002, 2001, "шт", Decimal("2.5")),
            ]
            loaded = await load_item_references(session, keys + keys[:1])
            assert count["n"] == 2
            assert set(loaded) == set(keys)
        finally:
            event.remove(bind, "before_cursor_execute", bump)


async def _submit(
    client: AsyncClient,
    token: str,
    client_id,
    items: list[dict],
) -> str:
    response = await client.post(
        "/api/v1/requests",
        headers=auth_header(token),
        json={
            "request_type": "normative",
            "client_id": str(client_id),
            "expiry_date": Request.add_months(date.today(), 3).isoformat(),
            "items": items,
        },
    )
    assert response.status_code == 201, response.text
    request_id = response.json()["data"]["id"]
    submit = await client.post(
        f"/api/v1/requests/{request_id}/submit",
        headers=auth_header(token),
    )
    assert submit.status_code == 200, submit.text
    return request_id


def _item(payload: dict, request_id: str, warehouse_code: int) -> dict:
    matched = next(row for row in payload["data"] if row["id"] == request_id)
    return next(
        row for row in matched["items"] if row["warehouse_code"] == warehouse_code
    )


async def test_pending_reference_columns(
    client: AsyncClient,
    test_user: AuthUser,
    pp_user: AuthUser,
    economist_user: AuthUser,
    catalog: dict[str, int],
) -> None:
    client_a = await ensure_client("ООО Справка НЗ")
    client_b = await ensure_client("ООО Справка чужая")
    system_id = await ensure_client("Общий клиент")
    warehouse = catalog["warehouse_code"]
    other_warehouse = catalog["warehouse_code_2"]
    previous_a: str | None = None
    previous_b: str | None = None
    pinned_a = False
    pinned_b = False
    starts = previous_month_starts(date.today())
    request_ids: list[str] = []
    try:
        previous_a = await _pin_loading_point(warehouse, POINT_A)
        pinned_a = True
        previous_b = await _pin_loading_point(other_warehouse, POINT_B)
        pinned_b = True
        await _ensure_product(PRODUCT, "Справочный артикул", Decimal("0.2500"))
        await _ensure_product(SYSTEM_PRODUCT, "Артикул общего клиента", Decimal("2.5"))
        async with AsyncSessionLocal() as session:
            await session.execute(
                delete(ActualShipment).where(
                    ActualShipment.product_code.in_([PRODUCT, SYSTEM_PRODUCT])
                )
            )
            await session.execute(
                delete(Normative).where(
                    Normative.product_code.in_([PRODUCT, SYSTEM_PRODUCT])
                )
            )
            active_until = Request.add_months(date.today(), 4)
            session.add_all(
                [
                    Normative(
                        product_code=PRODUCT,
                        warehouse_code=warehouse,
                        quantity=Decimal("400"),
                        unit="шт",
                        client_id=client_a,
                        client_name="ООО Справка НЗ",
                        expiry_date=active_until,
                        category="A",
                    ),
                    Normative(
                        product_code=PRODUCT,
                        warehouse_code=warehouse,
                        quantity=Decimal("0.200"),
                        unit="т",
                        client_id=client_a,
                        client_name="ООО Справка НЗ",
                        expiry_date=active_until,
                        category="A",
                    ),
                    Normative(
                        product_code=PRODUCT,
                        warehouse_code=warehouse,
                        quantity=Decimal("100"),
                        unit="кг",
                        client_id=client_b,
                        client_name="ООО Справка чужая",
                        expiry_date=active_until,
                        category="A",
                    ),
                    Normative(
                        product_code=PRODUCT,
                        warehouse_code=other_warehouse,
                        quantity=Decimal("800"),
                        unit="шт",
                        client_id=client_b,
                        client_name="ООО Справка чужая",
                        expiry_date=active_until,
                        category="A",
                    ),
                    Normative(
                        product_code=PRODUCT,
                        warehouse_code=warehouse,
                        quantity=Decimal("99999"),
                        unit="шт",
                        client_id=client_a,
                        client_name="ООО Справка НЗ",
                        expiry_date=active_until,
                        category="A",
                        deleted_at=datetime.now(UTC),
                    ),
                    Normative(
                        product_code=PRODUCT,
                        warehouse_code=warehouse,
                        quantity=Decimal("99999"),
                        unit="шт",
                        client_id=client_a,
                        client_name="ООО Справка НЗ",
                        expiry_date=date.today() - timedelta(days=1),
                        category="A",
                    ),
                    Normative(
                        product_code=PRODUCT,
                        warehouse_code=warehouse,
                        quantity=Decimal("99999"),
                        unit="шт",
                        client_id=client_a,
                        client_name="ООО Справка НЗ",
                        valid_from=date.today() + timedelta(days=1),
                        expiry_date=active_until,
                        category="A",
                    ),
                    Normative(
                        product_code=SYSTEM_PRODUCT,
                        warehouse_code=warehouse,
                        quantity=Decimal("10"),
                        unit="шт",
                        client_id=system_id,
                        client_name="Общий клиент",
                        expiry_date=active_until,
                        category="A",
                    ),
                    ActualShipment(
                        client_id=client_a,
                        product_code=PRODUCT,
                        quantity=Decimal("100"),
                        unit="кг",
                        shipment_date=_day(starts[1]),
                        loading_point=POINT_A,
                    ),
                    ActualShipment(
                        client_id=client_a,
                        product_code=PRODUCT,
                        quantity=Decimal("200"),
                        unit="кг",
                        shipment_date=_day(starts[3]),
                        loading_point=POINT_A,
                    ),
                    ActualShipment(
                        client_id=client_a,
                        product_code=PRODUCT,
                        quantity=Decimal("400"),
                        unit="шт",
                        shipment_date=_day(starts[4]),
                        loading_point=POINT_A,
                    ),
                    ActualShipment(
                        client_id=client_a,
                        product_code=PRODUCT,
                        quantity=Decimal("0.15"),
                        unit="т",
                        shipment_date=_day(starts[5]),
                        loading_point=POINT_A,
                    ),
                    ActualShipment(
                        client_id=client_b,
                        product_code=PRODUCT,
                        quantity=Decimal("50"),
                        unit="кг",
                        shipment_date=_day(starts[1]),
                        loading_point=POINT_A,
                    ),
                    ActualShipment(
                        client_id=client_b,
                        product_code=PRODUCT,
                        quantity=Decimal("1000"),
                        unit="кг",
                        shipment_date=_day(starts[0]),
                        loading_point=POINT_B,
                    ),
                    ActualShipment(
                        client_id=client_a,
                        product_code=PRODUCT,
                        quantity=Decimal("99999"),
                        unit="кг",
                        shipment_date=date.today(),
                        loading_point=POINT_A,
                    ),
                    ActualShipment(
                        client_id=client_a,
                        product_code=PRODUCT,
                        quantity=Decimal("99999"),
                        unit="кг",
                        shipment_date=_day(starts[2]),
                        loading_point=POINT_A,
                        deleted_at=datetime.now(UTC),
                    ),
                    ActualShipment(
                        client_id=client_a,
                        product_code=PRODUCT,
                        quantity=Decimal("99999"),
                        unit="кг",
                        shipment_date=_day(starts[2]),
                        loading_point="NONE",
                    ),
                ]
            )
            await session.commit()

        commercial = await login_token(client, test_user)
        pp = await login_token(client, pp_user)
        economist = await login_token(client, economist_user)
        tons_id = await _submit(
            client,
            commercial,
            client_a,
            [
                {
                    "product_code": PRODUCT,
                    "warehouse_code": warehouse,
                    "quantity_requested": 1,
                    "unit": "т",
                },
                {
                    "product_code": PRODUCT,
                    "warehouse_code": other_warehouse,
                    "quantity_requested": 1,
                    "unit": "т",
                },
            ],
        )
        pieces_id = await _submit(
            client,
            commercial,
            client_a,
            [
                {
                    "product_code": PRODUCT,
                    "warehouse_code": warehouse,
                    "quantity_requested": 10,
                    "unit": "шт",
                }
            ],
        )
        system_request_id = await _submit(
            client,
            commercial,
            system_id,
            [
                {
                    "product_code": SYSTEM_PRODUCT,
                    "warehouse_code": warehouse,
                    "quantity_requested": 1,
                    "unit": "шт",
                }
            ],
        )
        request_ids.extend([tons_id, pieces_id, system_request_id])

        pending = await client.get(
            "/api/v1/approvals/pp/pending",
            headers=auth_header(pp),
            params={"limit": 200},
        )
        assert pending.status_code == 200, pending.text
        payload = pending.json()
        _assert_coverage(
            _item(payload, tons_id, warehouse)["coverage"],
            {
                "existing_nz": 0.3,
                "monthly_sales": 0.11,
                "warehouse_monthly_sales": 0.12,
                "product_monthly_sales": 0.267,
            },
        )
        _assert_coverage(
            _item(payload, tons_id, other_warehouse)["coverage"],
            {
                "existing_nz": None,
                "monthly_sales": None,
                "warehouse_monthly_sales": 0.167,
                "product_monthly_sales": 0.267,
            },
        )
        _assert_coverage(
            _item(payload, pieces_id, warehouse)["coverage"],
            {
                "existing_nz": 1200,
                "monthly_sales": 440,
                "warehouse_monthly_sales": 480,
                "product_monthly_sales": 1067,
            },
        )
        system_row = next(
            row for row in payload["data"] if row["id"] == system_request_id
        )
        assert system_row["client_name"] == "Общий клиент"
        _assert_coverage(
            system_row["items"][0]["coverage"],
            {
                "existing_nz": 10,
                "monthly_sales": None,
                "warehouse_monthly_sales": None,
                "product_monthly_sales": None,
            },
        )

        approved = await client.post(
            f"/api/v1/approvals/pp/{tons_id}/action",
            headers=auth_header(pp),
            json={"action": "approve", "comment": "Объем подтвержден"},
        )
        assert approved.status_code == 200, approved.text
        economy = await client.get(
            "/api/v1/approvals/economy/pending",
            headers=auth_header(economist),
            params={"limit": 200},
        )
        assert economy.status_code == 200, economy.text
        _assert_coverage(
            _item(economy.json(), tons_id, warehouse)["coverage"],
            {
                "existing_nz": 0.3,
                "monthly_sales": 0.11,
                "warehouse_monthly_sales": 0.12,
                "product_monthly_sales": 0.267,
            },
        )

        await _set_weight(PRODUCT, Decimal("0"))
        without_weight = await client.get(
            "/api/v1/approvals/economy/pending",
            headers=auth_header(economist),
            params={"limit": 200},
        )
        assert without_weight.status_code == 200, without_weight.text
        _assert_coverage(
            _item(without_weight.json(), tons_id, warehouse)["coverage"],
            {
                "existing_nz": 0.2,
                "monthly_sales": 0.09,
                "warehouse_monthly_sales": 0.1,
                "product_monthly_sales": 0.25,
            },
        )
        pieces = await client.get(
            "/api/v1/approvals/pp/pending",
            headers=auth_header(pp),
            params={"limit": 200},
        )
        assert pieces.status_code == 200, pieces.text
        empty = {
            "existing_nz": None,
            "monthly_sales": None,
            "warehouse_monthly_sales": None,
            "product_monthly_sales": None,
        }
        _assert_coverage(
            _item(pieces.json(), pieces_id, warehouse)["coverage"],
            empty,
        )
    finally:
        for request_id in request_ids:
            await delete_request(request_id)
        async with AsyncSessionLocal() as session:
            await session.execute(
                delete(ActualShipment).where(
                    ActualShipment.product_code.in_([PRODUCT, SYSTEM_PRODUCT])
                )
            )
            await session.execute(
                delete(Normative).where(
                    Normative.product_code.in_([PRODUCT, SYSTEM_PRODUCT])
                )
            )
            await session.execute(
                delete(Product).where(Product.code.in_([PRODUCT, SYSTEM_PRODUCT]))
            )
            await session.commit()
        if pinned_a:
            await _restore_loading_point(warehouse, previous_a)
        if pinned_b:
            await _restore_loading_point(other_warehouse, previous_b)
