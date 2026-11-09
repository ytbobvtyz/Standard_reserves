"""Coverage inputs for an approval line.

Two statements cover the whole page: active normatives grouped by
client, product, warehouse and unit, and shipments grouped by client,
product, warehouse and month. Months of cover are calculated in the UI.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.actual_shipment import ActualShipment
from app.models.normative import Normative
from app.models.object import Object
from app.models.product import Product
from app.schemas.approval import ApprovalItemCoverage
from app.services.normatives import normative_active_on
from app.services.optimal_stock import (
    KG_IN_TON,
    MONTHS_IN_WINDOW,
    _month_after,
    average_monthly_kg,
    month_index,
    previous_month_starts,
)

TON_QUANT = Decimal("0.001")
PIECE_QUANT = Decimal("1")


@dataclass(frozen=True)
class ReferenceKey:
    client_id: UUID
    product_code: int
    warehouse_code: int
    unit: str
    weight_kg: Decimal


@dataclass
class _Mass:
    kg: Decimal = Decimal("0")
    pieces: Decimal = Decimal("0")
    has_mass: bool = False

    def add(self, quantity: Decimal, unit: str, weight_kg: Decimal) -> None:
        amount = Decimal(quantity)
        if unit == "шт":
            self.pieces += amount
            if weight_kg > 0:
                self.kg += amount * weight_kg
            return
        self.has_mass = True
        if unit == "т":
            self.kg += amount * KG_IN_TON
            return
        self.kg += amount


def _quantize(value: Decimal, unit: str) -> Decimal:
    step = PIECE_QUANT if unit == "шт" else TON_QUANT
    return value.quantize(step, rounding=ROUND_HALF_UP)


def _kg_to_unit(
    kg: Decimal | None,
    unit: str,
    weight_kg: Decimal,
) -> Decimal | None:
    if kg is None:
        return None
    if unit == "т":
        return _quantize(kg / KG_IN_TON, "т")
    if unit == "кг":
        return _quantize(kg, "т")
    if weight_kg <= 0:
        return None
    return _quantize(kg / weight_kg, "шт")


def _sales_value(
    series: list[Decimal] | None,
    unit: str,
    weight_kg: Decimal,
) -> Decimal | None:
    if series is None:
        return None
    return _kg_to_unit(_average_kg(series), unit, weight_kg)


def _mass_to_unit(
    mass: _Mass | None,
    unit: str,
    weight_kg: Decimal,
) -> Decimal | None:
    if mass is None:
        return None
    if unit == "шт":
        if weight_kg > 0:
            return _quantize(mass.kg / weight_kg, "шт")
        if mass.has_mass:
            return None
        return _quantize(mass.pieces, "шт")
    if mass.kg == 0 and mass.pieces > 0 and weight_kg <= 0:
        return None
    if unit == "кг":
        return _quantize(mass.kg, "т")
    return _quantize(mass.kg / KG_IN_TON, "т")


def _as_date(value: date | datetime) -> date:
    if isinstance(value, datetime):
        return value.date()
    return value


def _average_kg(series: list[Decimal] | None) -> Decimal | None:
    if not series:
        return None
    averaged = average_monthly_kg(series)
    if averaged is None:
        return None
    return averaged[0]


def _blank_months() -> list[Decimal]:
    return [Decimal("0")] * MONTHS_IN_WINDOW


async def load_item_references(
    db: AsyncSession,
    keys: list[ReferenceKey],
    *,
    today: date | None = None,
) -> dict[ReferenceKey, ApprovalItemCoverage]:
    unique = list(dict.fromkeys(keys))
    if not unique:
        return {}

    reference_day = today or date.today()
    product_codes = list({key.product_code for key in unique})
    weights = {key.product_code: key.weight_kg for key in unique}
    normative_rows = await _load_normative_groups(db, product_codes, reference_day)
    shipment_rows = await _load_shipment_months(db, product_codes, reference_day)

    client_nz: dict[tuple[UUID, int, int], _Mass] = defaultdict(_Mass)
    for row in normative_rows:
        weight = weights.get(row.product_code, Decimal("0"))
        client_nz[(row.client_id, row.product_code, row.warehouse_code)].add(
            Decimal(row.quantity), row.unit, weight
        )

    starts = previous_month_starts(reference_day)
    client_sales: dict[tuple[UUID, int, int], list[Decimal]] = defaultdict(
        _blank_months
    )
    warehouse_sales: dict[tuple[int, int], list[Decimal]] = defaultdict(_blank_months)
    product_sales: dict[int, list[Decimal]] = defaultdict(_blank_months)
    for row in shipment_rows:
        index = month_index(_as_date(row.month), starts)
        if index is None:
            continue
        kg = Decimal(row.kg or 0)
        client_key = (row.client_id, row.product_code, row.warehouse_code)
        warehouse_key = (row.product_code, row.warehouse_code)
        client_sales[client_key][index] += kg
        warehouse_sales[warehouse_key][index] += kg
        product_sales[row.product_code][index] += kg

    loaded: dict[ReferenceKey, ApprovalItemCoverage] = {}
    for key in unique:
        position = (key.client_id, key.product_code, key.warehouse_code)
        warehouse_key = (key.product_code, key.warehouse_code)
        loaded[key] = ApprovalItemCoverage(
            existing_nz=_mass_to_unit(
                client_nz.get(position),
                key.unit,
                key.weight_kg,
            ),
            monthly_sales=_sales_value(
                client_sales.get(position),
                key.unit,
                key.weight_kg,
            ),
            warehouse_monthly_sales=_sales_value(
                warehouse_sales.get(warehouse_key),
                key.unit,
                key.weight_kg,
            ),
            product_monthly_sales=_sales_value(
                product_sales.get(key.product_code),
                key.unit,
                key.weight_kg,
            ),
        )
    return loaded


async def _load_normative_groups(
    db: AsyncSession,
    product_codes: list[int],
    on_date: date,
):
    statement = (
        select(
            Normative.client_id,
            Normative.product_code,
            Normative.warehouse_code,
            Normative.unit,
            func.sum(Normative.quantity).label("quantity"),
        )
        .where(
            normative_active_on(on_date),
            Normative.product_code.in_(product_codes),
        )
        .group_by(
            Normative.client_id,
            Normative.product_code,
            Normative.warehouse_code,
            Normative.unit,
        )
    )
    return (await db.execute(statement)).all()


async def _load_shipment_months(
    db: AsyncSession,
    product_codes: list[int],
    on_date: date,
):
    starts = previous_month_starts(on_date)
    window_start = starts[0]
    current_month_start = _month_after(starts[-1])
    kilograms = case(
        (ActualShipment.unit == "кг", ActualShipment.quantity),
        (ActualShipment.unit == "т", ActualShipment.quantity * KG_IN_TON),
        else_=ActualShipment.quantity * func.coalesce(Product.weight_kg, 0),
    )
    month = func.date_trunc("month", ActualShipment.shipment_date)
    statement = (
        select(
            ActualShipment.client_id,
            ActualShipment.product_code,
            Object.code.label("warehouse_code"),
            month.label("month"),
            func.sum(kilograms).label("kg"),
        )
        .join(Product, Product.code == ActualShipment.product_code)
        .join(
            Object,
            and_(
                Object.loading_point == ActualShipment.loading_point,
                Object.type == "warehouse",
                Object.is_active.is_(True),
                Object.deleted_at.is_(None),
            ),
        )
        .where(
            ActualShipment.deleted_at.is_(None),
            ActualShipment.shipment_date >= window_start,
            ActualShipment.shipment_date < current_month_start,
            ActualShipment.product_code.in_(product_codes),
        )
        .group_by(
            ActualShipment.client_id,
            ActualShipment.product_code,
            Object.code,
            month,
        )
    )
    return (await db.execute(statement)).all()
