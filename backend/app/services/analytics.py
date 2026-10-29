"""Динамика запаса одного продукта: норматив, остаток и реализация.

Норматив — уровень запаса. На месяце он как есть. На неделе делится на 4,
на дне — на 28: так столбец сравнивается с продажами периода.
Реализация — сумма отгрузок периода, без накопления.
Остаток: на месяце — минимум, медиана и максимум дневных итогов.
На неделе — только минимум и максимум. На дне — запас этого дня.
Отрицательный доступный остаток перед суммой складов заменяется нулём.
Нет наблюдения — null, не ноль.

Тонны округляются до трёх знаков. Подразделение — clients.department_id.
Остаток не режется по клиенту и подразделению: снимок общий на склад и артикул.
Отгрузки склада отбираются по objects.loading_point.
"""

from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import APIError
from app.models.actual_shipment import ActualShipment
from app.models.available_balance_history import AvailableBalanceHistory
from app.models.client import Client
from app.models.normative import Normative
from app.models.object import Object
from app.models.product import Product
from app.models.production_request import ProductionRequest, ProductionRequestItem
from app.schemas.analytics import (
    Granularity,
    StockDynamicsBounds,
    StockDynamicsData,
    StockMonthSummary,
    StockSummaryData,
)
from app.services.dashboard import to_mass

ZERO = Decimal("0")
TONS = Decimal("0.001")
WEEK_NORMATIVE_DIVISOR = Decimal(4)
DAY_NORMATIVE_DIVISOR = Decimal(28)


def _round_tons(value: Decimal) -> Decimal:
    return value.quantize(TONS, rounding=ROUND_HALF_UP)


def _utc_date(value: datetime | date) -> date:
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            return value.astimezone(UTC).date()
        return value.date()
    return value


def _period_start(value: date, granularity: Granularity) -> date:
    if granularity == "day":
        return value
    if granularity == "week":
        return value - timedelta(days=value.weekday())
    return value.replace(day=1)


def _next_period(value: date, granularity: Granularity) -> date:
    if granularity == "day":
        return value + timedelta(days=1)
    if granularity == "week":
        return value + timedelta(days=7)
    if value.month == 12:
        return date(value.year + 1, 1, 1)
    return date(value.year, value.month + 1, 1)


def _period_end(value: date, granularity: Granularity) -> date:
    return _next_period(value, granularity) - timedelta(days=1)


def _iter_periods(
    date_from: date, date_to: date, granularity: Granularity
) -> list[date]:
    current = _period_start(date_from, granularity)
    end = _period_start(date_to, granularity)
    periods: list[date] = []
    while current <= end:
        periods.append(current)
        current = _next_period(current, granularity)
    return periods


def _bucket_bounds(
    period: date,
    granularity: Granularity,
    date_from: date,
    date_to: date,
) -> tuple[date, date]:
    start = max(period, date_from)
    end = min(_period_end(period, granularity), date_to)
    return start, end


def _check_period(date_from: date, date_to: date) -> None:
    if date_from > date_to:
        raise APIError(
            400,
            "VALIDATION_ERROR",
            "date_from не может быть позже date_to",
        )


def _tons(quantity: Decimal, unit: str, weight_kg: Decimal | None) -> Decimal:
    return to_mass(quantity, unit, weight_kg or ZERO, "т")


def _prorate_normative(total: Decimal, granularity: Granularity) -> Decimal:
    if granularity == "week":
        return total / WEEK_NORMATIVE_DIVISOR
    if granularity == "day":
        return total / DAY_NORMATIVE_DIVISOR
    return total


def _median(values: list[Decimal]) -> Decimal:
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / Decimal(2)


def _normative_start(
    created_at: datetime,
    production_item_id: UUID | None,
    valid_from: date | None,
    status: str | None,
    batch_deleted_at: datetime | None,
) -> date | None:
    if production_item_id is None:
        return _utc_date(created_at)
    if valid_from is None or status != "active" or batch_deleted_at is not None:
        return None
    return valid_from


async def _normative_rows(
    db: AsyncSession,
    *,
    product_code: int,
    warehouse_code: int | None,
    department_id: UUID | None,
    client_id: UUID | None,
    date_from: date | None,
    date_to: date | None,
):
    conditions = [
        Normative.deleted_at.is_(None),
        Normative.product_code == product_code,
    ]
    if date_from is not None:
        conditions.append(Normative.expiry_date >= date_from)
    if warehouse_code is not None:
        conditions.append(Normative.warehouse_code == warehouse_code)
    if department_id is not None:
        conditions.append(Client.department_id == department_id)
    if client_id is not None:
        conditions.append(Normative.client_id == client_id)
    stmt = (
        select(
            Normative.created_at,
            Normative.expiry_date,
            Normative.quantity,
            Normative.unit,
            Normative.production_request_item_id,
            Product.weight_kg,
            ProductionRequest.valid_from,
            ProductionRequest.status,
            ProductionRequest.deleted_at,
        )
        .join(Product, Product.code == Normative.product_code)
        .join(Client, Client.id == Normative.client_id)
        .outerjoin(
            ProductionRequestItem,
            ProductionRequestItem.id == Normative.production_request_item_id,
        )
        .outerjoin(
            ProductionRequest,
            ProductionRequest.id == ProductionRequestItem.production_request_id,
        )
        .where(*conditions)
    )
    return (await db.execute(stmt)).all()


def _normative_series(
    rows,
    periods: list[date],
    granularity: Granularity,
    date_from: date,
    date_to: date,
) -> list[Decimal | None]:
    totals = [ZERO for _ in periods]
    seen = [False for _ in periods]
    for row in rows:
        start = _normative_start(
            row.created_at,
            row.production_request_item_id,
            row.valid_from,
            row.status,
            row.deleted_at,
        )
        if start is None or start > date_to or row.expiry_date < date_from:
            continue
        mass = _tons(row.quantity, row.unit, row.weight_kg)
        for index, period in enumerate(periods):
            bucket_start, bucket_end = _bucket_bounds(
                period, granularity, date_from, date_to
            )
            if bucket_start > bucket_end:
                continue
            if start <= bucket_end and row.expiry_date >= bucket_start:
                totals[index] += mass
                seen[index] = True
    return [
        _round_tons(_prorate_normative(total, granularity)) if present else None
        for total, present in zip(totals, seen, strict=True)
    ]


async def _available_series(
    db: AsyncSession,
    *,
    product_code: int,
    warehouse_code: int | None,
    periods: list[date],
    granularity: Granularity,
    date_from: date,
    date_to: date,
) -> tuple[list[Decimal | None], list[Decimal | None], list[Decimal | None]]:
    """Минимум, медиана и максимум остатка внутри интервала точки.

    Месяц — по дневным итогам месяца. Неделя — минимум и максимум недели,
    без медианы. День отдаёт сам дневной итог в медиане.
    Отрицательный снимок склада заменяется нулём до суммы по складам.
    """
    conditions = [
        AvailableBalanceHistory.product_code == product_code,
        AvailableBalanceHistory.snapshot_date >= date_from,
        AvailableBalanceHistory.snapshot_date <= date_to,
    ]
    if warehouse_code is not None:
        conditions.append(AvailableBalanceHistory.warehouse_code == warehouse_code)
    rows = (
        await db.execute(
            select(
                AvailableBalanceHistory.snapshot_date,
                AvailableBalanceHistory.available,
                AvailableBalanceHistory.unit,
                Product.weight_kg,
            )
            .join(Product, Product.code == AvailableBalanceHistory.product_code)
            .where(*conditions)
        )
    ).all()
    daily: dict[date, Decimal] = {}
    for row in rows:
        mass = _tons(row.available, row.unit, row.weight_kg)
        if mass < ZERO:
            mass = ZERO
        daily[row.snapshot_date] = daily.get(row.snapshot_date, ZERO) + mass
    minimum: list[Decimal | None] = []
    median: list[Decimal | None] = []
    maximum: list[Decimal | None] = []
    for period in periods:
        start, end = _bucket_bounds(period, granularity, date_from, date_to)
        values = [total for day, total in daily.items() if start <= day <= end]
        if not values:
            minimum.append(None)
            median.append(None)
            maximum.append(None)
            continue
        if granularity == "day":
            minimum.append(None)
            median.append(_round_tons(values[0]))
            maximum.append(None)
            continue
        minimum.append(_round_tons(min(values)))
        maximum.append(_round_tons(max(values)))
        if granularity == "week":
            median.append(None)
            continue
        median.append(_round_tons(_median(values)))
    return minimum, median, maximum


async def _loading_point(db: AsyncSession, warehouse_code: int) -> str | None:
    return await db.scalar(
        select(Object.loading_point).where(
            Object.code == warehouse_code,
            Object.deleted_at.is_(None),
        )
    )


async def _actual_series(
    db: AsyncSession,
    *,
    product_code: int,
    warehouse_code: int | None,
    department_id: UUID | None,
    client_id: UUID | None,
    periods: list[date],
    granularity: Granularity,
    date_from: date,
    date_to: date,
) -> list[Decimal | None]:
    if warehouse_code is not None:
        loading_point = await _loading_point(db, warehouse_code)
        if not loading_point:
            return [None for _ in periods]
    else:
        loading_point = None
    conditions = [
        ActualShipment.deleted_at.is_(None),
        ActualShipment.product_code == product_code,
        ActualShipment.shipment_date >= date_from,
        ActualShipment.shipment_date <= date_to,
    ]
    if client_id is not None:
        conditions.append(ActualShipment.client_id == client_id)
    if department_id is not None:
        conditions.append(Client.department_id == department_id)
    if loading_point is not None:
        conditions.append(ActualShipment.loading_point == loading_point)
    stmt = select(
        ActualShipment.shipment_date,
        ActualShipment.quantity,
        ActualShipment.unit,
        Product.weight_kg,
    ).join(Product, Product.code == ActualShipment.product_code)
    if department_id is not None:
        stmt = stmt.join(Client, Client.id == ActualShipment.client_id)
    rows = (await db.execute(stmt.where(*conditions))).all()
    bucket_sum: dict[date, Decimal] = {}
    for row in rows:
        period = _period_start(row.shipment_date, granularity)
        mass = _tons(row.quantity, row.unit, row.weight_kg)
        bucket_sum[period] = bucket_sum.get(period, ZERO) + mass
    return [
        _round_tons(bucket_sum[period]) if period in bucket_sum else None
        for period in periods
    ]


async def _earliest_normative(
    db: AsyncSession,
    *,
    product_code: int,
    warehouse_code: int | None,
    department_id: UUID | None,
    client_id: UUID | None,
) -> date | None:
    rows = await _normative_rows(
        db,
        product_code=product_code,
        warehouse_code=warehouse_code,
        department_id=department_id,
        client_id=client_id,
        date_from=None,
        date_to=None,
    )
    starts = [
        start
        for row in rows
        if (
            start := _normative_start(
                row.created_at,
                row.production_request_item_id,
                row.valid_from,
                row.status,
                row.deleted_at,
            )
        )
        is not None
    ]
    return min(starts) if starts else None


async def _earliest_available(
    db: AsyncSession,
    *,
    product_code: int,
    warehouse_code: int | None,
) -> date | None:
    conditions = [AvailableBalanceHistory.product_code == product_code]
    if warehouse_code is not None:
        conditions.append(AvailableBalanceHistory.warehouse_code == warehouse_code)
    value = await db.scalar(
        select(func.min(AvailableBalanceHistory.snapshot_date)).where(*conditions)
    )
    return value


async def _earliest_shipment(
    db: AsyncSession,
    *,
    product_code: int,
    warehouse_code: int | None,
    department_id: UUID | None,
    client_id: UUID | None,
) -> date | None:
    if warehouse_code is not None:
        loading_point = await _loading_point(db, warehouse_code)
        if not loading_point:
            return None
    else:
        loading_point = None
    conditions = [
        ActualShipment.deleted_at.is_(None),
        ActualShipment.product_code == product_code,
    ]
    if client_id is not None:
        conditions.append(ActualShipment.client_id == client_id)
    if department_id is not None:
        conditions.append(Client.department_id == department_id)
    if loading_point is not None:
        conditions.append(ActualShipment.loading_point == loading_point)
    stmt = select(func.min(ActualShipment.shipment_date))
    if department_id is not None:
        stmt = stmt.join(Client, Client.id == ActualShipment.client_id)
    return await db.scalar(stmt.where(*conditions))


async def get_stock_bounds(
    db: AsyncSession,
    *,
    product_code: int,
    warehouse_code: int | None,
    department_id: UUID | None,
    client_id: UUID | None,
) -> StockDynamicsBounds:
    candidates = [
        await _earliest_normative(
            db,
            product_code=product_code,
            warehouse_code=warehouse_code,
            department_id=department_id,
            client_id=client_id,
        ),
        await _earliest_available(
            db,
            product_code=product_code,
            warehouse_code=warehouse_code,
        ),
        await _earliest_shipment(
            db,
            product_code=product_code,
            warehouse_code=warehouse_code,
            department_id=department_id,
            client_id=client_id,
        ),
    ]
    present = [item for item in candidates if item is not None]
    return StockDynamicsBounds(earliest_date=min(present) if present else None)


async def get_stock_dynamics(
    db: AsyncSession,
    *,
    product_code: int,
    warehouse_code: int | None,
    department_id: UUID | None,
    client_id: UUID | None,
    date_from: date,
    date_to: date,
    granularity: Granularity,
) -> StockDynamicsData:
    _check_period(date_from, date_to)
    periods = _iter_periods(date_from, date_to, granularity)
    rows = await _normative_rows(
        db,
        product_code=product_code,
        warehouse_code=warehouse_code,
        department_id=department_id,
        client_id=client_id,
        date_from=date_from,
        date_to=date_to,
    )
    normative = _normative_series(rows, periods, granularity, date_from, date_to)
    available_min, available_median, available_max = await _available_series(
        db,
        product_code=product_code,
        warehouse_code=warehouse_code,
        periods=periods,
        granularity=granularity,
        date_from=date_from,
        date_to=date_to,
    )
    actual = await _actual_series(
        db,
        product_code=product_code,
        warehouse_code=warehouse_code,
        department_id=department_id,
        client_id=client_id,
        periods=periods,
        granularity=granularity,
        date_from=date_from,
        date_to=date_to,
    )
    return StockDynamicsData(
        dates=periods,
        normative=normative,
        available_min=available_min,
        available_median=available_median,
        available_max=available_max,
        actual=actual,
        unit="т",
    )


def _month_starts(today: date, count: int = 6) -> list[date]:
    starts: list[date] = []
    year, month = today.year, today.month
    for offset in range(count - 1, -1, -1):
        index = month - offset
        year_shift, month_index = divmod(index - 1, 12)
        starts.append(date(year + year_shift, month_index + 1, 1))
    return starts


def _normative_intervals(rows) -> list[tuple[date, date, Decimal]]:
    intervals: list[tuple[date, date, Decimal]] = []
    for row in rows:
        start = _normative_start(
            row.created_at,
            row.production_request_item_id,
            row.valid_from,
            row.status,
            row.deleted_at,
        )
        if start is None:
            continue
        intervals.append(
            (start, row.expiry_date, _tons(row.quantity, row.unit, row.weight_kg))
        )
    return intervals


def _average_normative(
    intervals: list[tuple[date, date, Decimal]],
    start: date,
    end: date,
) -> Decimal | None:
    """Среднее дневного уровня норматива. День без норматива входит как ноль."""
    if start > end:
        return None
    total = ZERO
    seen = False
    days = 0
    cursor = start
    while cursor <= end:
        level = ZERO
        for begin, expiry, mass in intervals:
            if begin <= cursor <= expiry:
                level += mass
                seen = True
        total += level
        days += 1
        cursor += timedelta(days=1)
    if not seen:
        return None
    return _round_tons(total / Decimal(days))


async def get_stock_summary(
    db: AsyncSession,
    *,
    product_code: int,
    warehouse_code: int | None,
    department_id: UUID | None,
    client_id: UUID | None,
    today: date,
) -> StockSummaryData:
    """Шесть последних месяцев, включая текущий, по тем же фильтрам, что график."""
    periods = _month_starts(today)
    date_from = periods[0]
    _available_min, available_median, _available_max = await _available_series(
        db,
        product_code=product_code,
        warehouse_code=warehouse_code,
        periods=periods,
        granularity="month",
        date_from=date_from,
        date_to=today,
    )
    actual = await _actual_series(
        db,
        product_code=product_code,
        warehouse_code=warehouse_code,
        department_id=department_id,
        client_id=client_id,
        periods=periods,
        granularity="month",
        date_from=date_from,
        date_to=today,
    )
    rows = await _normative_rows(
        db,
        product_code=product_code,
        warehouse_code=warehouse_code,
        department_id=department_id,
        client_id=client_id,
        date_from=date_from,
        date_to=today,
    )
    intervals = _normative_intervals(rows)
    months = [
        StockMonthSummary(
            month=period,
            available_median=available_median[index],
            actual=actual[index],
            normative_avg=_average_normative(
                intervals,
                period,
                min(_period_end(period, "month"), today),
            ),
        )
        for index, period in enumerate(periods)
    ]
    return StockSummaryData(months=months, unit="т")
