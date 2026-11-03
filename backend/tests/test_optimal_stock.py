from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy import delete, select

from app.core.database import AsyncSessionLocal
from app.models.actual_shipment import ActualShipment
from app.models.normative import Normative
from app.models.object import Object
from app.models.product import Product
from app.models.production_request import ProductionRequest, ProductionRequestItem
from app.models.request import Request
from app.services.optimal_stock import (
    REASON_BELOW_PALLET,
    REASON_UNMAPPED,
    average_monthly_kg,
    pallet_threshold_kg,
    previous_month_starts,
    shipment_to_kg,
)
from tests.conftest import (
    AuthUser,
    auth_header,
    delete_request,
    ensure_client,
    login_token,
)

POINT = "Q058"


def test_average_uses_six_months_when_first_shipment_is_oldest() -> None:
    average, months = average_monthly_kg(
        [
            Decimal("10"),
            Decimal("0"),
            Decimal("0"),
            Decimal("0"),
            Decimal("0"),
            Decimal("20"),
        ]
    )
    assert months == 6
    assert average == Decimal("5.00")


def test_average_starts_at_first_month_with_shipment() -> None:
    average, months = average_monthly_kg(
        [
            Decimal("0"),
            Decimal("100"),
            Decimal("0"),
            Decimal("200"),
            Decimal("0"),
            Decimal("150"),
        ]
    )
    assert months == 5
    assert average == Decimal("90.00")


def test_average_uses_three_months_from_first_shipment() -> None:
    average, months = average_monthly_kg(
        [
            Decimal("0"),
            Decimal("0"),
            Decimal("0"),
            Decimal("100"),
            Decimal("0"),
            Decimal("50"),
        ]
    )
    assert months == 3
    assert average == Decimal("50.00")


def test_average_uses_one_month_when_only_previous_month_has_sales() -> None:
    average, months = average_monthly_kg(
        [
            Decimal("0"),
            Decimal("0"),
            Decimal("0"),
            Decimal("0"),
            Decimal("0"),
            Decimal("80"),
        ]
    )
    assert months == 1
    assert average == Decimal("80.00")


def test_average_is_empty_without_a_month_of_at_least_one_kg() -> None:
    assert (
        average_monthly_kg(
            [
                Decimal("0"),
                Decimal("0.4"),
                Decimal("0"),
                Decimal("0"),
                Decimal("0"),
                Decimal("0.9"),
            ]
        )
        is None
    )


def test_previous_months_exclude_the_current_month() -> None:
    starts = previous_month_starts(date(2026, 11, 2))
    assert starts == [
        date(2026, 5, 1),
        date(2026, 6, 1),
        date(2026, 7, 1),
        date(2026, 8, 1),
        date(2026, 9, 1),
        date(2026, 10, 1),
    ]


def test_pallet_threshold_needs_both_pallet_qty_and_weight() -> None:
    assert pallet_threshold_kg(None, Decimal("2.5")) is None
    assert pallet_threshold_kg(48, Decimal("0")) is None
    assert pallet_threshold_kg(48, None) is None
    assert pallet_threshold_kg(48, Decimal("2.5")) == Decimal("120.0")


def test_shipment_units_convert_to_kg() -> None:
    assert shipment_to_kg(Decimal("10"), "кг", Decimal("0.25")) == Decimal("10")
    assert shipment_to_kg(Decimal("0.15"), "т", Decimal("0.25")) == Decimal("150")
    assert shipment_to_kg(Decimal("400"), "шт", Decimal("0.25")) == Decimal("100")
    assert shipment_to_kg(Decimal("10"), "шт", Decimal("0")) == Decimal("0")


def _day(start: date) -> date:
    return start + timedelta(days=9)


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


async def _set_pallet(code: int, pallet_qty: int | None, weight_kg: Decimal) -> None:
    async with AsyncSessionLocal() as session:
        product = await session.get(Product, code)
        assert product is not None
        product.pallet_qty = pallet_qty
        product.weight_kg = weight_kg
        await session.commit()


async def test_calculate_optimal_average_pallet_and_empty(
    client: AsyncClient,
    test_user: AuthUser,
    logistics_user: AuthUser,
    catalog: dict[str, int],
) -> None:
    client_id = await ensure_client("ООО Расчёт запаса")
    previous_point = await _pin_loading_point(catalog["warehouse_code"], POINT)
    starts = previous_month_starts(date.today())
    product = catalog["product_code"]
    other = catalog["product_code_2"]
    warehouse = catalog["warehouse_code"]
    normative_id = uuid4()
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(
                delete(ActualShipment).where(ActualShipment.client_id == client_id)
            )
            session.add_all(
                [
                    ActualShipment(
                        client_id=client_id,
                        product_code=product,
                        quantity=Decimal("100"),
                        unit="кг",
                        shipment_date=_day(starts[1]),
                        loading_point=POINT,
                    ),
                    ActualShipment(
                        client_id=client_id,
                        product_code=product,
                        quantity=Decimal("200"),
                        unit="кг",
                        shipment_date=_day(starts[3]),
                        loading_point=POINT,
                    ),
                    ActualShipment(
                        client_id=client_id,
                        product_code=product,
                        quantity=Decimal("0.15"),
                        unit="т",
                        shipment_date=_day(starts[5]),
                        loading_point=POINT,
                    ),
                    ActualShipment(
                        client_id=client_id,
                        product_code=product,
                        quantity=Decimal("9999"),
                        unit="кг",
                        shipment_date=date.today(),
                        loading_point=POINT,
                    ),
                    ActualShipment(
                        client_id=client_id,
                        product_code=product,
                        quantity=Decimal("500"),
                        unit="кг",
                        shipment_date=_day(starts[5]),
                        loading_point="OTHR",
                    ),
                    ActualShipment(
                        client_id=client_id,
                        product_code=product,
                        quantity=Decimal("1000"),
                        unit="кг",
                        shipment_date=_day(starts[0]),
                        loading_point=POINT,
                        deleted_at=datetime.now(UTC),
                    ),
                ]
            )
            session.add(
                Normative(
                    id=normative_id,
                    product_code=other,
                    warehouse_code=warehouse,
                    quantity=Decimal("1000"),
                    unit="шт",
                    client_id=client_id,
                    client_name="ООО Расчёт запаса",
                    expiry_date=Request.add_months(date.today(), 4),
                    category="B",
                )
            )
            await session.commit()

        token = await login_token(client, test_user)
        body = {"client_id": str(client_id)}
        response = await client.post(
            "/api/v1/requests/calculate-optimal",
            headers=auth_header(token),
            json=body,
        )
        assert response.status_code == 200, response.text
        data = response.json()["data"]
        assert data["client_name"] == "ООО Расчёт запаса"
        assert data["items"] == [
            {
                "product_code": product,
                "warehouse_code": warehouse,
                "product_name": "Подшипник 6204ZZ",
                "warehouse_name": "Склад Ростов",
                "category": "A",
                "weight_kg": 0.25,
                "pallet_qty": None,
                "calculated_quantity": 90.0,
                "unit": "кг",
                "months_used": 5,
            }
        ]
        assert data["skipped_items"][0]["reason"] == REASON_UNMAPPED
        assert data["skipped_items"][0]["product_code"] == product
        assert other not in {row["product_code"] for row in data["items"]}
        assert data["existing_normatives"][0]["id"] == str(normative_id)
        assert data["existing_normatives"][0]["client_name"] == "ООО Расчёт запаса"

        await _set_pallet(product, 10000, Decimal("0.2500"))
        below = await client.post(
            "/api/v1/requests/calculate-optimal",
            headers=auth_header(token),
            json=body,
        )
        assert below.status_code == 200, below.text
        skipped = below.json()["data"]["skipped_items"]
        assert REASON_BELOW_PALLET in {row["reason"] for row in skipped}
        assert below.json()["data"]["items"] == []

        await _set_pallet(product, None, Decimal("0"))
        no_pallet = await client.post(
            "/api/v1/requests/calculate-optimal",
            headers=auth_header(token),
            json=body,
        )
        assert no_pallet.status_code == 200, no_pallet.text
        assert no_pallet.json()["data"]["items"][0]["calculated_quantity"] == 90.0

        await _set_pallet(product, 48, Decimal("0"))
        zero_weight = await client.post(
            "/api/v1/requests/calculate-optimal",
            headers=auth_header(token),
            json=body,
        )
        assert zero_weight.status_code == 200, zero_weight.text
        assert zero_weight.json()["data"]["items"][0]["months_used"] == 5
        assert REASON_BELOW_PALLET not in {
            row["reason"] for row in zero_weight.json()["data"]["skipped_items"]
        }

        forbidden = await client.post(
            "/api/v1/requests/calculate-optimal",
            headers=auth_header(await login_token(client, logistics_user)),
            json=body,
        )
        assert forbidden.status_code == 403
    finally:
        async with AsyncSessionLocal() as session:
            await session.execute(
                delete(ActualShipment).where(ActualShipment.client_id == client_id)
            )
            await session.execute(delete(Normative).where(Normative.id == normative_id))
            product_row = await session.get(Product, product)
            assert product_row is not None
            product_row.pallet_qty = None
            product_row.weight_kg = Decimal("0.2500")
            await session.commit()
        await _restore_loading_point(catalog["warehouse_code"], previous_point)


async def _approve(
    client: AsyncClient,
    commercial_token: str,
    pp_token: str,
    economist_token: str,
    *,
    client_id,
    auto_complete: bool,
    catalog: dict[str, int],
) -> str:
    payload: dict = {
        "request_type": "normative",
        "client_id": str(client_id),
        "expiry_date": Request.add_months(date.today(), 3).isoformat(),
        "items": [
            {
                "product_code": catalog["product_code"],
                "warehouse_code": catalog["warehouse_code"],
                "quantity_requested": 10,
                "unit": "шт",
            }
        ],
    }
    created = await client.post(
        "/api/v1/requests",
        headers=auth_header(commercial_token),
        json=payload,
    )
    assert created.status_code == 201, created.text
    assert created.json()["data"]["auto_complete_previous"] is False
    request_id = created.json()["data"]["id"]
    submitted = await client.post(
        f"/api/v1/requests/{request_id}/submit",
        headers=auth_header(commercial_token),
        json={"auto_complete_previous": auto_complete},
    )
    assert submitted.status_code == 200, submitted.text
    pp = await client.post(
        f"/api/v1/approvals/pp/{request_id}/action",
        headers=auth_header(pp_token),
        json={"action": "approve", "comment": "ок"},
    )
    assert pp.status_code == 200, pp.text
    economy = await client.post(
        f"/api/v1/approvals/economy/{request_id}/action",
        headers=auth_header(economist_token),
        json={"action": "approve", "comment": "ок"},
    )
    assert economy.status_code == 200, economy.text
    assert economy.json()["data"]["status"] == "active"
    return request_id


async def test_approve_closes_commercial_normatives_and_keeps_excel(
    client: AsyncClient,
    test_user: AuthUser,
    pp_user: AuthUser,
    economist_user: AuthUser,
    catalog: dict[str, int],
) -> None:
    client_id = await ensure_client("ООО Закрыть нормативы")
    other_client = await ensure_client("ООО Чужой норматив")
    old_request_id = uuid4()
    other_request_id = uuid4()
    foreign_request_id = uuid4()
    matched_id = uuid4()
    sibling_id = uuid4()
    other_norm_id = uuid4()
    foreign_id = uuid4()
    excel_norm_id = uuid4()
    batch_id = uuid4()
    item_id = uuid4()
    excel_expiry = Request.add_months(date.today(), 5)
    old_expiry = Request.add_months(date.today(), 4)
    request_id: str | None = None
    try:
        async with AsyncSessionLocal() as session:
            session.add(
                Request(
                    id=old_request_id,
                    request_type="normative",
                    status="active",
                    client_id=client_id,
                    client_name="ООО Закрыть нормативы",
                    initiator_id=test_user.id,
                    expiry_date=old_expiry,
                )
            )
            session.add(
                Request(
                    id=other_request_id,
                    request_type="normative",
                    status="active",
                    client_id=client_id,
                    client_name="ООО Закрыть нормативы",
                    initiator_id=test_user.id,
                    expiry_date=old_expiry,
                )
            )
            session.add(
                Request(
                    id=foreign_request_id,
                    request_type="normative",
                    status="active",
                    client_id=other_client,
                    client_name="ООО Чужой норматив",
                    initiator_id=test_user.id,
                    expiry_date=old_expiry,
                )
            )
            session.add(
                Normative(
                    id=matched_id,
                    request_id=old_request_id,
                    product_code=catalog["product_code"],
                    warehouse_code=catalog["warehouse_code"],
                    quantity=Decimal("1000"),
                    unit="шт",
                    client_id=client_id,
                    client_name="ООО Закрыть нормативы",
                    expiry_date=old_expiry,
                    category="A",
                )
            )
            session.add(
                Normative(
                    id=sibling_id,
                    request_id=old_request_id,
                    product_code=catalog["product_code_2"],
                    warehouse_code=catalog["warehouse_code"],
                    quantity=Decimal("30"),
                    unit="шт",
                    client_id=client_id,
                    client_name="ООО Закрыть нормативы",
                    expiry_date=old_expiry,
                    category="B",
                )
            )
            session.add(
                Normative(
                    id=other_norm_id,
                    request_id=other_request_id,
                    product_code=catalog["product_code_2"],
                    warehouse_code=catalog["warehouse_code_2"],
                    quantity=Decimal("15"),
                    unit="шт",
                    client_id=client_id,
                    client_name="ООО Закрыть нормативы",
                    expiry_date=old_expiry,
                    category="B",
                )
            )
            session.add(
                Normative(
                    id=foreign_id,
                    request_id=foreign_request_id,
                    product_code=catalog["product_code"],
                    warehouse_code=catalog["warehouse_code"],
                    quantity=Decimal("50"),
                    unit="шт",
                    client_id=other_client,
                    client_name="ООО Чужой норматив",
                    expiry_date=old_expiry,
                    category="A",
                )
            )
            session.add(
                ProductionRequest(
                    id=batch_id,
                    uploaded_by=test_user.id,
                    client_id=client_id,
                    client_name="ООО Закрыть нормативы",
                    valid_from=date.today() - timedelta(days=10),
                    valid_to=excel_expiry,
                    status="active",
                )
            )
            session.add(
                ProductionRequestItem(
                    id=item_id,
                    production_request_id=batch_id,
                    product_code=catalog["product_code"],
                    warehouse_code=catalog["warehouse_code_2"],
                    quantity=Decimal("20"),
                    unit="шт",
                    client_id=client_id,
                    client_name="ООО Закрыть нормативы",
                    category="A",
                )
            )
            session.add(
                Normative(
                    id=excel_norm_id,
                    production_request_item_id=item_id,
                    product_code=catalog["product_code"],
                    warehouse_code=catalog["warehouse_code_2"],
                    quantity=Decimal("20"),
                    unit="шт",
                    client_id=client_id,
                    client_name="ООО Закрыть нормативы",
                    expiry_date=excel_expiry,
                    category="A",
                )
            )
            await session.commit()

        request_id = await _approve(
            client,
            await login_token(client, test_user),
            await login_token(client, pp_user),
            await login_token(client, economist_user),
            client_id=client_id,
            auto_complete=True,
            catalog=catalog,
        )

        async with AsyncSessionLocal() as session:
            matched = await session.get(Normative, matched_id)
            sibling = await session.get(Normative, sibling_id)
            other_norm = await session.get(Normative, other_norm_id)
            excel = await session.get(Normative, excel_norm_id)
            foreign = await session.get(Normative, foreign_id)
            old_request = await session.get(Request, old_request_id)
            other_request = await session.get(Request, other_request_id)
            created = (
                await session.scalars(
                    select(Normative).where(
                        Normative.request_id == request_id,
                        Normative.deleted_at.is_(None),
                    )
                )
            ).all()
            assert matched is not None and sibling is not None
            assert matched.expiry_date == date.today()
            assert sibling.expiry_date == date.today()
            assert matched.deleted_at is None
            assert sibling.deleted_at is None
            assert old_request is not None
            assert old_request.expiry_date == date.today()
            assert other_norm is not None and other_request is not None
            assert other_norm.expiry_date == old_expiry
            assert other_request.expiry_date == old_expiry
            assert excel is not None
            assert excel.expiry_date == excel_expiry
            assert excel.deleted_at is None
            assert foreign is not None
            assert foreign.expiry_date == old_expiry
            assert len(created) == 1
            assert created[0].valid_from == date.today() + timedelta(days=1)
            assert created[0].expiry_date == Request.add_months(date.today(), 3)
    finally:
        if request_id is not None:
            await delete_request(request_id)
        for leftover in (old_request_id, other_request_id, foreign_request_id):
            await delete_request(leftover)
        async with AsyncSessionLocal() as session:
            await session.execute(
                delete(Normative).where(Normative.id == excel_norm_id)
            )
            await session.execute(
                delete(ProductionRequestItem).where(ProductionRequestItem.id == item_id)
            )
            await session.execute(
                delete(ProductionRequest).where(ProductionRequest.id == batch_id)
            )
            await session.commit()


async def test_approve_without_flag_keeps_previous_normatives(
    client: AsyncClient,
    test_user: AuthUser,
    pp_user: AuthUser,
    economist_user: AuthUser,
    catalog: dict[str, int],
) -> None:
    client_id = await ensure_client("ООО Без автозавершения")
    old_request_id = uuid4()
    old_id = uuid4()
    old_expiry = Request.add_months(date.today(), 4)
    request_id: str | None = None
    try:
        async with AsyncSessionLocal() as session:
            session.add(
                Request(
                    id=old_request_id,
                    request_type="normative",
                    status="active",
                    client_id=client_id,
                    client_name="ООО Без автозавершения",
                    initiator_id=test_user.id,
                    expiry_date=old_expiry,
                )
            )
            session.add(
                Normative(
                    id=old_id,
                    request_id=old_request_id,
                    product_code=catalog["product_code"],
                    warehouse_code=catalog["warehouse_code"],
                    quantity=Decimal("80"),
                    unit="шт",
                    client_id=client_id,
                    client_name="ООО Без автозавершения",
                    expiry_date=old_expiry,
                    category="A",
                )
            )
            await session.commit()
        request_id = await _approve(
            client,
            await login_token(client, test_user),
            await login_token(client, pp_user),
            await login_token(client, economist_user),
            client_id=client_id,
            auto_complete=False,
            catalog=catalog,
        )
        async with AsyncSessionLocal() as session:
            old = await session.get(Normative, old_id)
            old_request = await session.get(Request, old_request_id)
            created = (
                await session.scalars(
                    select(Normative).where(Normative.request_id == request_id)
                )
            ).one()
            assert old is not None and old_request is not None
            assert old.expiry_date == old_expiry
            assert old.deleted_at is None
            assert old_request.expiry_date == old_expiry
            assert created.valid_from == date.today() + timedelta(days=1)
            assert created.deleted_at is None
    finally:
        if request_id is not None:
            await delete_request(request_id)
        await delete_request(old_request_id)
