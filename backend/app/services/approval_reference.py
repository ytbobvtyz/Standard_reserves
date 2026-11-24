"""Coverage inputs for an approval line.

Three statements cover the whole page: the related-article chain,
active normatives grouped by client, product and warehouse, and
shipments grouped by client, product, warehouse and month. Months of
cover are calculated in the UI.

Normatives stay on the requested article. Sales totals add the related
articles found by the same walk as get_related_products.
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
from app.schemas.approval import ApprovalItemCoverage, ApprovalRelatedProduct
from app.services.normatives import normative_active_on
from app.services.optimal_stock import (
    KG_IN_TON,
    MONTHS_IN_WINDOW,
    _month_after,
    average_monthly_kg,
    month_index,
    previous_month_starts,
)
from app.services.references import load_related_by_codes

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
class ItemReference:
    coverage: ApprovalItemCoverage
    avg_sales_client_total: Decimal
    avg_sales_client_related: Decimal
    avg_sales_product_warehouse_total: Decimal
    avg_sales_product_warehouse_related: Decimal
    avg_sales_product_all_warehouses_total: Decimal
    avg_sales_product_all_warehouses_related: Decimal
    related_products: list[ApprovalRelatedProduct]


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


def _sales_or_zero(
    series: list[Decimal] | None,
    unit: str,
    weight_kg: Decimal,
) -> Decimal:
    value = _sales_value(series, unit, weight_kg)
    if value is None:
        return Decimal("0")
    return value


def _sum_series(parts: list[list[Decimal] | None]) -> list[Decimal] | None:
    present = [part for part in parts if part is not None]
    if not present:
        return None
    total = _blank_months()
    for part in present:
        for index, value in enumerate(part):
            total[index] += value
    return total


def empty_item_reference() -> ItemReference:
    zero = Decimal("0")
    return ItemReference(
        coverage=ApprovalItemCoverage(),
        avg_sales_client_total=zero,
        avg_sales_client_related=zero,
        avg_sales_product_warehouse_total=zero,
        avg_sales_product_warehouse_related=zero,
        avg_sales_product_all_warehouses_total=zero,
        avg_sales_product_all_warehouses_related=zero,
        related_products=[],
    )


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
) -> dict[ReferenceKey, ItemReference]:
    unique = list(dict.fromkeys(keys))
    if not unique:
        return {}

    reference_day = today or date.today()
    product_codes = list({key.product_code for key in unique})
    weights = {key.product_code: key.weight_kg for key in unique}
    related_map = await load_related_by_codes(db, product_codes)
    shipment_codes = set(product_codes)
    for related in related_map.values():
        shipment_codes.update(code for code, _name in related)
    # Normatives stay on the requested article. Shipments include the group.
    normative_rows = await _load_normative_groups(db, product_codes, reference_day)
    shipment_rows = await _load_shipment_months(
        db, sorted(shipment_codes), reference_day
    )

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

    loaded: dict[ReferenceKey, ItemReference] = {}
    for key in unique:
        position = (key.client_id, key.product_code, key.warehouse_code)
        warehouse_key = (key.product_code, key.warehouse_code)
        related = related_map.get(key.product_code, [])
        related_codes = [code for code, _name in related]
        group_codes = [key.product_code, *related_codes]
        client_group = _sum_series(
            [
                client_sales.get((key.client_id, code, key.warehouse_code))
                for code in group_codes
            ]
        )
        client_related = _sum_series(
            [
                client_sales.get((key.client_id, code, key.warehouse_code))
                for code in related_codes
            ]
        )
        warehouse_group = _sum_series(
            [warehouse_sales.get((code, key.warehouse_code)) for code in group_codes]
        )
        warehouse_related = _sum_series(
            [warehouse_sales.get((code, key.warehouse_code)) for code in related_codes]
        )
        product_group = _sum_series([product_sales.get(code) for code in group_codes])
        product_related = _sum_series(
            [product_sales.get(code) for code in related_codes]
        )

        loaded[key] = ItemReference(
            coverage=ApprovalItemCoverage(
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
            ),
            avg_sales_client_total=_sales_or_zero(
                client_group, key.unit, key.weight_kg
            ),
            avg_sales_client_related=_sales_or_zero(
                client_related, key.unit, key.weight_kg
            ),
            avg_sales_product_warehouse_total=_sales_or_zero(
                warehouse_group, key.unit, key.weight_kg
            ),
            avg_sales_product_warehouse_related=_sales_or_zero(
                warehouse_related, key.unit, key.weight_kg
            ),
            avg_sales_product_all_warehouses_total=_sales_or_zero(
                product_group, key.unit, key.weight_kg
            ),
            avg_sales_product_all_warehouses_related=_sales_or_zero(
                product_related, key.unit, key.weight_kg
            ),
            related_products=[
                ApprovalRelatedProduct(
                    code=code,
                    name=name,
                    avg_sales=_sales_or_zero(
                        client_sales.get((key.client_id, code, key.warehouse_code)),
                        key.unit,
                        key.weight_kg,
                    ),
                    avg_sales_warehouse=_sales_or_zero(
                        warehouse_sales.get((code, key.warehouse_code)),
                        key.unit,
                        key.weight_kg,
                    ),
                    avg_sales_all_warehouses=_sales_or_zero(
                        product_sales.get(code),
                        key.unit,
                        key.weight_kg,
                    ),
                )
                for code, name in related
            ],
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
