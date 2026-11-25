"""Аналитика одного клиента: норматив и фактические отгрузки.

Норматив на графике — исторический уровень, как на `/analytics`:
месяц без деления, неделя / 4, день / 28. Реализация — сумма отгрузок
бакета, без накопления и без остатков склада.

Покрытие строк и среза — то же окно, что у согласования экономиста:
предыдущие 6 календарных месяцев, текущий не входит, среднее с первого
месяца, где отгрузка не меньше 1 кг. Родственники входят в делитель
артикула и среза, только если переключатель включён. В строке склада
они уже сидят в отгрузках этого склада, поэтому переключатель её не меняет.

Пункт отгрузки без активного склада не входит в строки складов и в
среднемесячную артикула. Он остаётся отдельной строкой и попадает в
график, только когда склады не сужены.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.actual_shipment import ActualShipment
from app.models.normative import Normative
from app.models.object import Object
from app.models.product import Product
from app.models.production_request import ProductionRequest, ProductionRequestItem
from app.schemas.analytics import (
    ClientAnalyticsChart,
    ClientAnalyticsData,
    ClientAnalyticsSlice,
    ClientProductRow,
    ClientRelatedSales,
    ClientUnmatchedPoint,
    ClientWarehouseRow,
    Granularity,
)
from app.services.analytics import (
    ZERO,
    _check_period,
    _iter_periods,
    _normative_series,
    _normative_start,
    _period_start,
    _round_tons,
    _tons,
)
from app.services.clients import get_client
from app.services.optimal_stock import (
    MONTHS_IN_WINDOW,
    average_monthly_kg,
    month_index,
    previous_month_starts,
    shipment_to_kg,
)
from app.services.references import load_related_by_codes

COVERAGE_STEP = Decimal("0.1")


@dataclass
class _Norm:
    row: object
    product_code: int
    warehouse_code: int
    product_name: str
    start: date
    expiry: date
    tons: Decimal
    active: bool
    intersects: bool


@dataclass
class _Ship:
    product_code: int
    warehouse_code: int | None
    loading_point: str
    shipment_date: date
    kg: Decimal
    tons: Decimal


def _blank_months() -> list[Decimal]:
    return [ZERO for _ in range(MONTHS_IN_WINDOW)]


def _add_month(store: dict, key: object, index: int, kg: Decimal) -> None:
    slot = store.get(key)
    if slot is None:
        slot = _blank_months()
        store[key] = slot
    slot[index] += kg


def _add_period(totals: dict, seen: dict, key: object, tons: Decimal) -> None:
    totals[key] = totals.get(key, ZERO) + tons
    seen[key] = True


def _sum_series(series: list[list[Decimal] | None]) -> list[Decimal]:
    total = _blank_months()
    for item in series:
        if item is None:
            continue
        for index, value in enumerate(item):
            total[index] += value
    return total


def _avg_tons(monthly_kg: list[Decimal] | None) -> Decimal | None:
    if monthly_kg is None:
        return None
    averaged = average_monthly_kg(monthly_kg)
    if averaged is None:
        return None
    kilograms, _months = averaged
    tons = _round_tons(kilograms / Decimal(1000))
    if tons <= ZERO:
        return None
    return tons


def _period_tons(total: Decimal, seen: bool) -> Decimal | None:
    if not seen:
        return None
    return _round_tons(total)


def _coverage(normative: Decimal, average: Decimal | None) -> Decimal | None:
    if average is None or average <= ZERO:
        return None
    return (normative / average).quantize(COVERAGE_STEP, rounding=ROUND_HALF_UP)


def _outside(
    normative: Decimal,
    average: Decimal | None,
    period: Decimal | None,
) -> bool:
    return normative == ZERO and (average is not None or period is not None)


def _metric(
    normative: Decimal,
    monthly_kg: list[Decimal] | None,
    period_total: Decimal,
    period_seen: bool,
) -> tuple[Decimal, Decimal | None, Decimal | None, Decimal | None, bool]:
    rounded = _round_tons(normative)
    average = _avg_tons(monthly_kg)
    period = _period_tons(period_total, period_seen)
    return (
        rounded,
        average,
        period,
        _coverage(rounded, average),
        _outside(rounded, average, period),
    )


def _codes(values: list[int] | None) -> set[int] | None:
    if values is None:
        return None
    return set(values)


def _selected(code: int, chosen: set[int] | None) -> bool:
    return chosen is None or code in chosen


def _window_end(today: date, date_to: date) -> date:
    previous_month_end = today.replace(day=1) - timedelta(days=1)
    return max(date_to, previous_month_end)


async def get_client_analytics(
    db: AsyncSession,
    *,
    client_id: UUID,
    date_from: date,
    date_to: date,
    warehouse_codes: list[int] | None,
    product_codes: list[int] | None,
    include_related: bool,
    granularity: Granularity,
    today: date | None = None,
) -> ClientAnalyticsData:
    _check_period(date_from, date_to)
    client = await get_client(db, client_id)
    current = today or datetime.now(UTC).date()
    month_starts = previous_month_starts(current)
    products = _codes(product_codes)
    warehouses = _codes(warehouse_codes)
    selection_empty = (products is not None and not products) or (
        warehouses is not None and not warehouses
    )

    norms, names = await _load_normatives(
        db,
        client_id=client_id,
        date_from=date_from,
        date_to=date_to,
        today=current,
    )
    ships = await _load_shipments(
        db,
        client_id=client_id,
        date_from=min(month_starts[0], date_from),
        date_to=_window_end(current, date_to),
        names=names,
    )
    warehouse_names = await _warehouse_names(db)
    related = await load_related_by_codes(
        db,
        [item.product_code for item in norms] + [item.product_code for item in ships],
    )

    mapped_months: dict[int, list[Decimal]] = {}
    warehouse_months: dict[int, list[Decimal]] = {}
    unmatched_months: dict[str, list[Decimal]] = {}
    product_period: dict[int, Decimal] = {}
    product_seen: dict[int, bool] = {}
    warehouse_period: dict[int, Decimal] = {}
    warehouse_seen: dict[int, bool] = {}
    unmatched_period: dict[str, Decimal] = {}
    unmatched_seen: dict[str, bool] = {}
    seen_products = {item.product_code for item in norms}
    seen_warehouses = {item.warehouse_code for item in norms}

    for ship in ships:
        index = month_index(ship.shipment_date, month_starts)
        in_period = date_from <= ship.shipment_date <= date_to
        if ship.warehouse_code is None:
            if index is not None:
                _add_month(unmatched_months, ship.loading_point, index, ship.kg)
            if in_period:
                _add_period(
                    unmatched_period, unmatched_seen, ship.loading_point, ship.tons
                )
        else:
            seen_warehouses.add(ship.warehouse_code)
            if index is not None:
                _add_month(mapped_months, ship.product_code, index, ship.kg)
                _add_month(warehouse_months, ship.warehouse_code, index, ship.kg)
            if in_period:
                _add_period(
                    warehouse_period, warehouse_seen, ship.warehouse_code, ship.tons
                )
        if index is not None or in_period:
            seen_products.add(ship.product_code)
        if in_period:
            _add_period(product_period, product_seen, ship.product_code, ship.tons)

    warehouse_rows = _warehouse_rows(
        seen_warehouses,
        norms,
        warehouse_months,
        warehouse_period,
        warehouse_seen,
        warehouse_names,
    )
    product_rows = _product_rows(
        seen_products,
        norms,
        mapped_months,
        product_period,
        product_seen,
        names,
        related,
        include_related,
    )
    unmatched_rows = _unmatched_rows(
        unmatched_months,
        unmatched_period,
        unmatched_seen,
    )
    periods = _iter_periods(date_from, date_to, granularity)
    chart, slice_data = _chart_and_slice(
        norms=norms,
        ships=ships,
        periods=periods,
        granularity=granularity,
        date_from=date_from,
        date_to=date_to,
        month_starts=month_starts,
        products=products,
        warehouses=warehouses,
        related=related,
        include_related=include_related,
        selection_empty=selection_empty,
    )
    department = client.department.name if client.department is not None else None
    return ClientAnalyticsData(
        client_id=client.id,
        client_name=client.name,
        department_name=department,
        is_system=client.is_system,
        chart=chart,
        slice=slice_data,
        warehouses=warehouse_rows,
        products=product_rows,
        unmatched=unmatched_rows,
    )


async def _load_normatives(
    db: AsyncSession,
    *,
    client_id: UUID,
    date_from: date,
    date_to: date,
    today: date,
) -> tuple[list[_Norm], dict[int, str]]:
    rows = (
        await db.execute(
            select(
                Normative.product_code,
                Normative.warehouse_code,
                Normative.created_at,
                Normative.expiry_date,
                Normative.quantity,
                Normative.unit,
                Normative.production_request_item_id,
                Normative.valid_from.label("commercial_valid_from"),
                Product.name.label("product_name"),
                Product.weight_kg,
                ProductionRequest.valid_from.label("batch_valid_from"),
                ProductionRequest.status,
                ProductionRequest.deleted_at,
            )
            .join(Product, Product.code == Normative.product_code)
            .outerjoin(
                ProductionRequestItem,
                ProductionRequestItem.id == Normative.production_request_item_id,
            )
            .outerjoin(
                ProductionRequest,
                ProductionRequest.id == ProductionRequestItem.production_request_id,
            )
            .where(
                Normative.client_id == client_id,
                Normative.deleted_at.is_(None),
            )
        )
    ).all()
    names: dict[int, str] = {}
    loaded: list[_Norm] = []
    for row in rows:
        names[row.product_code] = row.product_name
        start = _normative_start(
            row.created_at,
            row.production_request_item_id,
            row.commercial_valid_from,
            row.batch_valid_from,
            row.status,
            row.deleted_at,
        )
        if start is None:
            continue
        loaded.append(
            _Norm(
                row=row,
                product_code=row.product_code,
                warehouse_code=row.warehouse_code,
                product_name=row.product_name,
                start=start,
                expiry=row.expiry_date,
                tons=_tons(row.quantity, row.unit, row.weight_kg),
                active=start <= today <= row.expiry_date,
                intersects=start <= date_to and row.expiry_date >= date_from,
            )
        )
    return [item for item in loaded if item.active or item.intersects], names


async def _load_shipments(
    db: AsyncSession,
    *,
    client_id: UUID,
    date_from: date,
    date_to: date,
    names: dict[int, str],
) -> list[_Ship]:
    rows = (
        await db.execute(
            select(
                ActualShipment.product_code,
                ActualShipment.quantity,
                ActualShipment.unit,
                ActualShipment.shipment_date,
                ActualShipment.loading_point,
                Product.name,
                Product.weight_kg,
            )
            .join(Product, Product.code == ActualShipment.product_code)
            .where(
                ActualShipment.client_id == client_id,
                ActualShipment.deleted_at.is_(None),
                ActualShipment.shipment_date >= date_from,
                ActualShipment.shipment_date <= date_to,
            )
        )
    ).all()
    points = await _active_loading_points(db)
    ships: list[_Ship] = []
    for row in rows:
        names[row.product_code] = row.name
        ships.append(
            _Ship(
                product_code=row.product_code,
                warehouse_code=points.get(row.loading_point),
                loading_point=row.loading_point,
                shipment_date=row.shipment_date,
                kg=shipment_to_kg(row.quantity, row.unit, row.weight_kg),
                tons=_tons(row.quantity, row.unit, row.weight_kg),
            )
        )
    return ships


async def _active_loading_points(db: AsyncSession) -> dict[str, int]:
    rows = (
        await db.execute(
            select(Object.code, Object.loading_point).where(
                Object.type == "warehouse",
                Object.deleted_at.is_(None),
                Object.is_active.is_(True),
                Object.loading_point.is_not(None),
            )
        )
    ).all()
    return {row.loading_point: row.code for row in rows if row.loading_point}


async def _warehouse_names(db: AsyncSession) -> dict[int, str]:
    rows = (
        await db.execute(
            select(Object.code, Object.name).where(Object.deleted_at.is_(None))
        )
    ).all()
    return {row.code: row.name for row in rows}


def _warehouse_rows(
    seen: set[int],
    norms: list[_Norm],
    months: dict[int, list[Decimal]],
    period: dict[int, Decimal],
    period_seen: dict[int, bool],
    names: dict[int, str],
) -> list[ClientWarehouseRow]:
    current: dict[int, Decimal] = defaultdict(lambda: ZERO)
    for item in norms:
        if item.active:
            current[item.warehouse_code] += item.tons
    rows: list[ClientWarehouseRow] = []
    for code in seen:
        normative, average, flow, coverage, outside = _metric(
            current[code],
            months.get(code),
            period.get(code, ZERO),
            period_seen.get(code, False),
        )
        rows.append(
            ClientWarehouseRow(
                code=code,
                name=names.get(code, str(code)),
                normative_tons=normative,
                avg_monthly_tons=average,
                period_tons=flow,
                coverage_months=coverage,
                outside_normative=outside,
            )
        )
    rows.sort(key=lambda item: (item.name, item.code))
    return rows


def _product_rows(
    seen: set[int],
    norms: list[_Norm],
    months: dict[int, list[Decimal]],
    period: dict[int, Decimal],
    period_seen: dict[int, bool],
    names: dict[int, str],
    related: dict[int, list[tuple[int, str]]],
    include_related: bool,
) -> list[ClientProductRow]:
    current: dict[int, Decimal] = defaultdict(lambda: ZERO)
    for item in norms:
        if item.active:
            current[item.product_code] += item.tons
    rows: list[ClientProductRow] = []
    for code in seen:
        family = [code]
        related_rows: list[ClientRelatedSales] = []
        for related_code, related_name in related.get(code, []):
            related_rows.append(
                ClientRelatedSales(
                    code=related_code,
                    name=related_name,
                    avg_monthly_tons=_avg_tons(months.get(related_code)),
                )
            )
            if include_related:
                family.append(related_code)
        normative, average, flow, coverage, outside = _metric(
            current[code],
            _sum_series([months.get(item) for item in family]),
            period.get(code, ZERO),
            period_seen.get(code, False),
        )
        rows.append(
            ClientProductRow(
                code=code,
                name=names.get(code, str(code)),
                normative_tons=normative,
                avg_monthly_tons=average,
                period_tons=flow,
                coverage_months=coverage,
                outside_normative=outside,
                related=related_rows,
            )
        )
    rows.sort(key=lambda item: item.code)
    return rows


def _unmatched_rows(
    months: dict[str, list[Decimal]],
    period: dict[str, Decimal],
    period_seen: dict[str, bool],
) -> list[ClientUnmatchedPoint]:
    points = set(months) | {point for point, present in period_seen.items() if present}
    rows: list[ClientUnmatchedPoint] = []
    for point in points:
        _normative, average, flow, coverage, outside = _metric(
            ZERO,
            months.get(point),
            period.get(point, ZERO),
            period_seen.get(point, False),
        )
        if average is None and flow is None:
            continue
        rows.append(
            ClientUnmatchedPoint(
                loading_point=point,
                avg_monthly_tons=average,
                period_tons=flow,
                coverage_months=coverage,
                outside_normative=outside,
            )
        )
    rows.sort(key=lambda item: item.loading_point)
    return rows


def _chart_and_slice(
    *,
    norms: list[_Norm],
    ships: list[_Ship],
    periods: list[date],
    granularity: Granularity,
    date_from: date,
    date_to: date,
    month_starts: list[date],
    products: set[int] | None,
    warehouses: set[int] | None,
    related: dict[int, list[tuple[int, str]]],
    include_related: bool,
    selection_empty: bool,
) -> tuple[ClientAnalyticsChart, ClientAnalyticsSlice]:
    if selection_empty:
        return (
            ClientAnalyticsChart(
                dates=periods,
                normative=[None for _ in periods],
                actual=[None for _ in periods],
            ),
            ClientAnalyticsSlice(
                normative_tons=ZERO,
                avg_monthly_tons=None,
                period_tons=None,
                coverage_months=None,
                outside_normative=False,
            ),
        )

    chosen_norms = [
        item
        for item in norms
        if _selected(item.product_code, products)
        and _selected(item.warehouse_code, warehouses)
    ]
    normative_series = _normative_series(
        [item.row for item in chosen_norms],
        periods,
        granularity,
        date_from,
        date_to,
    )
    bucket: dict[date, Decimal] = {}
    period_total = ZERO
    period_seen = False
    for ship in ships:
        if not _ship_on_chart(ship, products, warehouses):
            continue
        if not (date_from <= ship.shipment_date <= date_to):
            continue
        period_seen = True
        period_total += ship.tons
        period = _period_start(ship.shipment_date, granularity)
        bucket[period] = bucket.get(period, ZERO) + ship.tons
    actual_series = [
        _round_tons(bucket[period]) if period in bucket else None for period in periods
    ]
    normative_now = _round_tons(
        sum((item.tons for item in chosen_norms if item.active), ZERO)
    )
    average = _slice_average(
        ships,
        month_starts,
        products,
        warehouses,
        related,
        include_related,
    )
    flow = _period_tons(period_total, period_seen)
    return (
        ClientAnalyticsChart(
            dates=periods,
            normative=normative_series,
            actual=actual_series,
        ),
        ClientAnalyticsSlice(
            normative_tons=normative_now,
            avg_monthly_tons=average,
            period_tons=flow,
            coverage_months=_coverage(normative_now, average),
            outside_normative=_outside(normative_now, average, flow),
        ),
    )


def _ship_on_chart(
    ship: _Ship,
    products: set[int] | None,
    warehouses: set[int] | None,
) -> bool:
    if not _selected(ship.product_code, products):
        return False
    if warehouses is None:
        return True
    return ship.warehouse_code is not None and ship.warehouse_code in warehouses


def _slice_average(
    ships: list[_Ship],
    month_starts: list[date],
    products: set[int] | None,
    warehouses: set[int] | None,
    related: dict[int, list[tuple[int, str]]],
    include_related: bool,
) -> Decimal | None:
    family = products
    if products is not None and include_related:
        family = set(products)
        for code in products:
            family.update(related_code for related_code, _name in related.get(code, []))
    monthly = _blank_months()
    seen = False
    for ship in ships:
        if family is not None and ship.product_code not in family:
            continue
        if not _ship_on_chart(ship, None, warehouses):
            continue
        index = month_index(ship.shipment_date, month_starts)
        if index is None:
            continue
        monthly[index] += ship.kg
        seen = True
    if not seen:
        return None
    return _avg_tons(monthly)
