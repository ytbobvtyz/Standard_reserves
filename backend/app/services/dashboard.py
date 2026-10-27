from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal
from uuid import UUID

from sqlalchemy import Date, and_, cast, exists, func, or_, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import text

from app.models.available_balance import AvailableBalance
from app.models.client import Client
from app.models.department import Department
from app.models.normative import Normative
from app.models.object import Object
from app.models.product import Product
from app.models.production_request import ProductionRequest, ProductionRequestItem
from app.schemas.common import PaginationMeta
from app.schemas.dashboard import (
    DashboardExceptionItem,
    DashboardNorthStar,
    ExpiryCalendarData,
    ExpiryCalendarDay,
    GroupBy,
    MassUnit,
    NormativeTrendData,
    NzByDepartmentData,
    NzByDepartmentItem,
    NzByDepartmentWarehouse,
    TopClientItem,
    TopClientsData,
    TrendPoint,
    TrendSeries,
    WarehouseCoverageData,
    WarehouseCoverageItem,
)
from app.services.logistics_normative import collect_deficit_rows, to_pieces

ZERO = Decimal("0")
HUNDRED = Decimal("100")
KG_IN_TON = Decimal("1000")
CRITICAL_SHARE = Decimal("0.4")
DEFAULT_FUTURE_DAYS = 180
TOP_SKU_SERIES = 9
OTHERS_LABEL = "Остальные"


def _quantize_pct(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _round_kpi_mass(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)


def _coverage_ratio(total: Decimal, deficit: Decimal) -> Decimal:
    if total == 0:
        return ZERO
    value = (total - deficit) / total * HUNDRED
    if value <= 0:
        return ZERO
    if value >= HUNDRED:
        return HUNDRED
    return _quantize_pct(value)


def _quantize_mass(value: Decimal, unit: MassUnit) -> Decimal:
    step = Decimal("0.000001") if unit == "т" else Decimal("0.001")
    return value.quantize(step, rounding=ROUND_HALF_UP)


def to_mass(
    quantity: Decimal, source_unit: str, weight_kg: Decimal, target: MassUnit
) -> Decimal:
    pieces = to_pieces(quantity, source_unit, weight_kg)
    kilograms = pieces * (weight_kg or ZERO)
    if target == "кг":
        return _quantize_mass(kilograms, "кг")
    return _quantize_mass(kilograms / KG_IN_TON, "т")


def _period_start(value: date, group_by: GroupBy) -> date:
    if group_by == "day":
        return value
    if group_by == "week":
        return value - timedelta(days=value.weekday())
    return value.replace(day=1)


def _next_period(value: date, group_by: GroupBy) -> date:
    if group_by == "day":
        return value + timedelta(days=1)
    if group_by == "week":
        return value + timedelta(days=7)
    if value.month == 12:
        return date(value.year + 1, 1, 1)
    return date(value.year, value.month + 1, 1)


def _period_end(value: date, group_by: GroupBy) -> date:
    return _next_period(value, group_by) - timedelta(days=1)


def _iter_periods(date_from: date, date_to: date, group_by: GroupBy) -> list[date]:
    current = _period_start(date_from, group_by)
    end = _period_start(date_to, group_by)
    periods: list[date] = []
    while current <= end:
        periods.append(current)
        current = _next_period(current, group_by)
    return periods


def _default_range(group_by: GroupBy, today: date) -> tuple[date, date]:
    end = today + timedelta(days=DEFAULT_FUTURE_DAYS)
    if group_by == "day":
        return today - timedelta(days=29), end
    if group_by == "week":
        return _period_start(today - timedelta(weeks=11), "week"), end
    month_cursor = date(today.year, today.month, 1)
    for _ in range(11):
        month_cursor = (
            date(month_cursor.year - 1, 12, 1)
            if month_cursor.month == 1
            else date(month_cursor.year, month_cursor.month - 1, 1)
        )
    return month_cursor, end


def _to_date(value: object) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


async def refresh_mv_normative_daily(db: AsyncSession) -> None:
    await db.execute(text("SELECT refresh_mv_normative_daily_job()"))


def _active_conditions():
    today = date.today()
    excel_ok = exists(
        select(1)
        .select_from(ProductionRequestItem)
        .join(
            ProductionRequest,
            ProductionRequest.id == ProductionRequestItem.production_request_id,
        )
        .where(
            ProductionRequestItem.id == Normative.production_request_item_id,
            ProductionRequest.deleted_at.is_(None),
            ProductionRequest.status == "active",
            ProductionRequest.valid_from <= today,
        )
    )
    return [
        Normative.deleted_at.is_(None),
        Normative.expiry_date >= today,
        or_(Normative.production_request_item_id.is_(None), excel_ok),
    ]


def _validity_start(created_at: datetime, valid_from: date | None) -> date:
    if valid_from is not None:
        return valid_from
    return _to_date(created_at)


async def _kpi_position_masses(
    db: AsyncSession,
    *,
    unit: MassUnit,
    warehouse_code: int | None,
    department_id: UUID | None,
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    """Норматив, дефицит к плану, дефицит к доступному и истекающие 30 дней."""
    today = date.today()
    horizon = today + timedelta(days=30)
    conditions = _active_conditions()
    if warehouse_code is not None:
        conditions.append(Normative.warehouse_code == warehouse_code)
    if department_id is not None:
        conditions.append(Client.department_id == department_id)
    rows = (
        await db.execute(
            select(
                Normative.warehouse_code,
                Normative.product_code,
                Normative.quantity,
                Normative.unit,
                Normative.expiry_date,
                Product.weight_kg,
            )
            .join(Product, Product.code == Normative.product_code)
            .join(Client, Client.id == Normative.client_id)
            .where(*conditions)
        )
    ).all()
    total = ZERO
    expiring = ZERO
    positions: dict[tuple[int, int], dict[str, Decimal]] = {}
    for warehouse, product, quantity, source_unit, expiry, weight in rows:
        weight_kg = weight or ZERO
        mass = to_mass(quantity, source_unit, weight_kg, unit)
        total += mass
        if expiry <= horizon:
            expiring += mass
        slot = positions.setdefault(
            (warehouse, product),
            {"norm": ZERO, "weight": weight_kg},
        )
        slot["norm"] += mass
        slot["weight"] = weight_kg
    balances: dict[tuple[int, int], AvailableBalance] = {}
    if positions:
        balances = {
            (item.warehouse_code, item.product_code): item
            for item in (
                await db.execute(
                    select(AvailableBalance).where(
                        tuple_(
                            AvailableBalance.warehouse_code,
                            AvailableBalance.product_code,
                        ).in_(list(positions))
                    )
                )
            )
            .scalars()
            .all()
        }
    deficit_transfers = ZERO
    deficit_available = ZERO
    for key, slot in positions.items():
        balance = balances.get(key)
        weight_kg = slot["weight"]
        if balance is None:
            plan_mass = ZERO
            available_mass = ZERO
        else:
            plan_mass = to_mass(balance.plan, balance.unit, weight_kg, unit)
            available_mass = to_mass(balance.available, balance.unit, weight_kg, unit)
        deficit_transfers += max(ZERO, slot["norm"] - plan_mass)
        deficit_available += max(ZERO, slot["norm"] - available_mass)
    return total, deficit_transfers, deficit_available, expiring


async def get_summary(
    db: AsyncSession,
    *,
    unit: MassUnit = "т",
    warehouse_code: int | None = None,
    department_id: UUID | None = None,
) -> DashboardNorthStar:
    conditions = _active_conditions()
    if warehouse_code is not None:
        conditions.append(Normative.warehouse_code == warehouse_code)
    if department_id is not None:
        conditions.append(Client.department_id == department_id)
    today = date.today()
    horizon = today + timedelta(days=30)
    stats = (
        await db.execute(
            select(
                func.count(Normative.id),
                func.avg(Normative.expiry_date - today),
                func.count(Normative.id).filter(Normative.expiry_date <= horizon),
            )
            .select_from(Normative)
            .join(Client, Client.id == Normative.client_id)
            .where(*conditions)
        )
    ).one()
    active_count = int(stats[0] or 0)
    avg_days = stats[1]
    expiring_30d = int(stats[2] or 0)

    total, deficit_transfers, deficit_available, expiring_mass = (
        await _kpi_position_masses(
            db,
            unit=unit,
            warehouse_code=warehouse_code,
            department_id=department_id,
        )
    )
    active_quantity = _round_kpi_mass(total)
    deficit_quantity = _round_kpi_mass(deficit_transfers)
    expiring_quantity = _round_kpi_mass(expiring_mass)
    coverage_with_transfers = _coverage_ratio(active_quantity, deficit_quantity)
    coverage_available_only = _coverage_ratio(
        active_quantity, _round_kpi_mass(deficit_available)
    )
    avg_remaining = None
    if avg_days is not None:
        avg_remaining = Decimal(str(avg_days)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    return DashboardNorthStar(
        active_count=active_count,
        active_quantity=active_quantity,
        deficit_quantity=deficit_quantity,
        coverage_pct=coverage_with_transfers,
        coverage_with_transfers=coverage_with_transfers,
        coverage_available_only=coverage_available_only,
        expiring_30d=expiring_30d,
        expiring_30d_quantity=expiring_quantity,
        avg_remaining_days=avg_remaining,
        unit=unit,
    )


async def get_normative_trend(
    db: AsyncSession,
    *,
    product_code: int | None,
    warehouse_code: int | None,
    date_from: date | None,
    date_to: date | None,
    group_by: GroupBy,
    unit: MassUnit = "т",
    department_id: UUID | None = None,
    client_id: UUID | None = None,
) -> NormativeTrendData:
    today = date.today()
    if date_from is None or date_to is None:
        default_from, default_to = _default_range(group_by, today)
        date_from = date_from or default_from
        date_to = date_to or default_to
    if date_from > date_to:
        date_from, date_to = date_to, date_from

    created_date = cast(Normative.created_at, Date)
    commercial_in_range = and_(
        Normative.production_request_item_id.is_(None),
        created_date <= date_to,
    )
    excel_in_range = and_(
        Normative.production_request_item_id.is_not(None),
        ProductionRequest.deleted_at.is_(None),
        ProductionRequest.status == "active",
        ProductionRequest.valid_from <= date_to,
    )
    conditions = [
        Normative.deleted_at.is_(None),
        Product.deleted_at.is_(None),
        Object.deleted_at.is_(None),
        Normative.expiry_date >= date_from,
        or_(commercial_in_range, excel_in_range),
    ]
    if product_code is not None:
        conditions.append(Normative.product_code == product_code)
    if warehouse_code is not None:
        conditions.append(Normative.warehouse_code == warehouse_code)
    if department_id is not None:
        conditions.append(Client.department_id == department_id)
    if client_id is not None:
        conditions.append(Normative.client_id == client_id)

    stmt = (
        select(Normative, ProductionRequest.valid_from)
        .options(
            selectinload(Normative.product),
            selectinload(Normative.warehouse),
        )
        .join(Product, Product.code == Normative.product_code)
        .join(Object, Object.code == Normative.warehouse_code)
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
    rows = (await db.execute(stmt)).all()
    periods = _iter_periods(date_from, date_to, group_by)
    split_by_product = warehouse_code is not None and product_code is None
    grouped: dict[tuple, dict[date, list[Decimal]]] = {}
    counts: dict[tuple, dict[date, int]] = {}

    for normative, valid_from in rows:
        start = _validity_start(normative.created_at, valid_from)
        if start > date_to or normative.expiry_date < date_from:
            continue
        product = normative.product
        warehouse = normative.warehouse
        sku = product.code if split_by_product else None
        sku_name = product.name if split_by_product else None
        key = (warehouse.code, warehouse.name, sku, sku_name)
        mass = to_mass(normative.quantity, normative.unit, product.weight_kg, unit)
        bucket = grouped.setdefault(key, {})
        count_bucket = counts.setdefault(key, {})
        for period in periods:
            overlaps = (
                start <= _period_end(period, group_by)
                and normative.expiry_date >= period
            )
            if overlaps:
                bucket.setdefault(period, []).append(mass)
                count_bucket[period] = count_bucket.get(period, 0) + 1

    series: list[TrendSeries] = []
    for key, points_map in grouped.items():
        wh_code, wh_name, sku, sku_name = key
        series_key = f"warehouse:{wh_code}"
        if sku is not None:
            series_key = f"product:{sku}:warehouse:{wh_code}"
        count_bucket = counts[key]
        series.append(
            TrendSeries(
                key=series_key,
                warehouse_code=wh_code,
                warehouse_name=wh_name,
                product_code=sku,
                product_name=sku_name,
                points=[
                    TrendPoint(
                        period=period,
                        total_normative=_quantize_mass(
                            sum(points_map.get(period, []), ZERO), unit
                        ),
                        count_active=count_bucket.get(period, 0),
                    )
                    for period in periods
                ],
            )
        )
    if split_by_product:
        series = _collapse_top_skus(series, periods, unit)
    else:
        series.sort(key=lambda item: item.warehouse_name)
    return NormativeTrendData(
        group_by=group_by,
        date_from=date_from,
        date_to=date_to,
        unit=unit,
        periods=periods,
        series=series,
    )


def _series_total(series: TrendSeries) -> Decimal:
    return sum((point.total_normative for point in series.points), ZERO)


def _collapse_top_skus(
    series: list[TrendSeries], periods: list[date], unit: MassUnit
) -> list[TrendSeries]:
    ranked = sorted(series, key=_series_total, reverse=True)
    if len(ranked) <= TOP_SKU_SERIES:
        return ranked
    keep = ranked[:TOP_SKU_SERIES]
    rest = ranked[TOP_SKU_SERIES:]
    warehouse = keep[0]
    others = TrendSeries(
        key=f"product:other:warehouse:{warehouse.warehouse_code}",
        warehouse_code=warehouse.warehouse_code,
        warehouse_name=warehouse.warehouse_name,
        product_code=None,
        product_name=OTHERS_LABEL,
        points=[
            TrendPoint(
                period=period,
                total_normative=_quantize_mass(
                    sum(
                        (
                            next(
                                (
                                    point.total_normative
                                    for point in item.points
                                    if point.period == period
                                ),
                                ZERO,
                            )
                            for item in rest
                        ),
                        ZERO,
                    ),
                    unit,
                ),
                count_active=sum(
                    next(
                        (
                            point.count_active
                            for point in item.points
                            if point.period == period
                        ),
                        0,
                    )
                    for item in rest
                ),
            )
            for period in periods
        ],
    )
    return keep + [others]


def _exception_status(
    deficit: Decimal, requirement: Decimal
) -> Literal["critical", "attention"]:
    if requirement <= 0:
        return "critical"
    if deficit / requirement >= CRITICAL_SHARE:
        return "critical"
    return "attention"


async def _request_ids_for_keys(
    db: AsyncSession, keys: list[tuple[int, int]]
) -> dict[tuple[int, int], UUID]:
    if not keys:
        return {}
    rows = (
        await db.execute(
            select(
                Normative.warehouse_code,
                Normative.product_code,
                Normative.request_id,
            )
            .where(
                Normative.deleted_at.is_(None),
                Normative.request_id.is_not(None),
                tuple_(Normative.warehouse_code, Normative.product_code).in_(keys),
            )
            .order_by(Normative.created_at.desc())
        )
    ).all()
    mapping: dict[tuple[int, int], UUID] = {}
    for warehouse_code, product_code, request_id in rows:
        key = (warehouse_code, product_code)
        if key not in mapping and request_id is not None:
            mapping[key] = request_id
    return mapping


async def list_exceptions(
    db: AsyncSession,
    *,
    warehouse_code: int | None = None,
    product_code: int | None = None,
    page: int = 1,
    limit: int = 50,
    unit: MassUnit = "т",
    department_id: UUID | None = None,
) -> tuple[list[DashboardExceptionItem], PaginationMeta]:
    rows = await collect_deficit_rows(
        db,
        warehouse_code=warehouse_code,
        product_codes=[product_code] if product_code is not None else None,
        filter_mode="deficit_only",
        department_id=department_id,
    )
    items: list[DashboardExceptionItem] = []
    keys: list[tuple[int, int]] = []
    for row in rows:
        if row.hide_group_metrics or row.deficit <= 0:
            continue
        if product_code is not None and row.product_code != product_code:
            continue
        keys.append((row.warehouse_code, row.product_code))
        items.append(
            DashboardExceptionItem(
                product_code=row.product_code,
                product_name=row.product_name,
                warehouse_code=row.warehouse_code,
                warehouse_name=row.warehouse_name,
                normative_quantity=to_mass(
                    row.normative_quantity, "шт", row.weight_kg, unit
                ),
                requirement=to_mass(row.requirement, "шт", row.weight_kg, unit),
                available=to_mass(row.available, "шт", row.weight_kg, unit),
                plan=to_mass(row.plan, "шт", row.weight_kg, unit),
                deficit=to_mass(row.deficit, "шт", row.weight_kg, unit),
                unit=unit,
                status=_exception_status(row.deficit, row.requirement),
                request_id=None,
            )
        )
    request_ids = await _request_ids_for_keys(db, keys)
    for item in items:
        item.request_id = request_ids.get((item.warehouse_code, item.product_code))
    items.sort(key=lambda item: item.deficit, reverse=True)
    total = len(items)
    start = (page - 1) * limit
    return items[start : start + limit], PaginationMeta(
        page=page, limit=limit, total=total
    )


async def get_warehouse_coverage(
    db: AsyncSession,
    *,
    unit: MassUnit = "т",
    warehouse_code: int | None = None,
    department_id: UUID | None = None,
    client_id: UUID | None = None,
) -> WarehouseCoverageData:
    scoped = department_id is not None or client_id is not None
    rows = await collect_deficit_rows(
        db,
        filter_mode="all",
        warehouse_code=warehouse_code,
        department_id=department_id,
        client_id=client_id,
        scope_to_normative_keys=scoped,
    )
    buckets: dict[int, dict[str, Decimal | str]] = {}
    for row in rows:
        bucket = buckets.setdefault(
            row.warehouse_code,
            {
                "warehouse_name": row.warehouse_name,
                "normative": ZERO,
                "available": ZERO,
                "deficit": ZERO,
                "requirement": ZERO,
                "plan": ZERO,
            },
        )
        bucket["available"] = bucket["available"] + to_mass(
            row.available, "шт", row.weight_kg, unit
        )
        bucket["plan"] = bucket["plan"] + to_mass(row.plan, "шт", row.weight_kg, unit)
        if row.hide_group_metrics:
            continue
        bucket["normative"] = bucket["normative"] + to_mass(
            row.normative_quantity, "шт", row.weight_kg, unit
        )
        bucket["requirement"] = bucket["requirement"] + to_mass(
            row.requirement, "шт", row.weight_kg, unit
        )
        if row.deficit > 0:
            bucket["deficit"] = bucket["deficit"] + to_mass(
                row.deficit, "шт", row.weight_kg, unit
            )
    items: list[WarehouseCoverageItem] = []
    for code, bucket in buckets.items():
        requirement = Decimal(str(bucket["requirement"]))
        plan = Decimal(str(bucket["plan"]))
        available = Decimal(str(bucket["available"]))
        planned = max(ZERO, plan - available)
        normative = Decimal(str(bucket["normative"]))
        deficit = Decimal(str(bucket["deficit"]))
        stack = available + planned + deficit
        if scoped:
            coverage = _coverage_ratio(normative, deficit)
        elif requirement <= 0:
            coverage = HUNDRED
        else:
            coverage = min(HUNDRED, _quantize_pct(plan / requirement * HUNDRED))
        items.append(
            WarehouseCoverageItem(
                warehouse_code=code,
                warehouse_name=str(bucket["warehouse_name"]),
                normative_quantity=_quantize_mass(normative, unit),
                available=_quantize_mass(available, unit),
                planned=_quantize_mass(planned, unit),
                deficit=_quantize_mass(deficit, unit),
                requirement=_quantize_mass(requirement, unit),
                coverage_pct=coverage,
                mismatch=stack > normative,
                unit=unit,
            )
        )
    items.sort(key=lambda item: (item.deficit, item.available), reverse=True)
    return WarehouseCoverageData(unit=unit, warehouses=items)


async def get_expiry_calendar(
    db: AsyncSession,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    unit: MassUnit = "т",
    warehouse_code: int | None = None,
    department_id: UUID | None = None,
) -> ExpiryCalendarData:
    today = date.today()
    start = date_from or today
    end = date_to or (today + timedelta(days=89))
    if start > end:
        start, end = end, start
    conditions = _active_conditions()
    if warehouse_code is not None:
        conditions.append(Normative.warehouse_code == warehouse_code)
    if department_id is not None:
        conditions.append(Client.department_id == department_id)
    conditions.extend(
        [
            Normative.expiry_date >= start,
            Normative.expiry_date <= end,
        ]
    )
    rows = (
        await db.execute(
            select(Normative, Product.weight_kg)
            .join(Product, Product.code == Normative.product_code)
            .join(Client, Client.id == Normative.client_id)
            .where(*conditions)
        )
    ).all()
    by_day: dict[date, list[Decimal]] = {}
    counts: dict[date, int] = {}
    for normative, weight_kg in rows:
        mass = to_mass(normative.quantity, normative.unit, weight_kg, unit)
        by_day.setdefault(normative.expiry_date, []).append(mass)
        counts[normative.expiry_date] = counts.get(normative.expiry_date, 0) + 1
    days = [
        ExpiryCalendarDay(
            date=day,
            count=counts[day],
            quantity=_quantize_mass(sum(values, ZERO), unit),
        )
        for day, values in sorted(by_day.items())
    ]
    return ExpiryCalendarData(date_from=start, date_to=end, unit=unit, days=days)


NO_DEPARTMENT = "Без управления"


async def _active_normative_rows(
    db: AsyncSession,
    unit: MassUnit,
    *,
    department_id: UUID | None = None,
    warehouse_code: int | None = None,
):
    conditions = _active_conditions()
    if department_id is not None:
        conditions.append(Client.department_id == department_id)
    if warehouse_code is not None:
        conditions.append(Normative.warehouse_code == warehouse_code)
    result = await db.execute(
        select(
            Normative.quantity,
            Normative.unit,
            Normative.warehouse_code,
            Object.name,
            Product.weight_kg,
            Client.id,
            Client.client_code,
            Client.name,
            Client.inn,
            Client.department_id,
            Department.name,
        )
        .join(Product, Product.code == Normative.product_code)
        .join(Object, Object.code == Normative.warehouse_code)
        .join(Client, Client.id == Normative.client_id)
        .outerjoin(Department, Department.id == Client.department_id)
        .where(*conditions)
    )
    return result.all(), unit


def _department_total(item: NzByDepartmentItem) -> Decimal:
    return sum((warehouse.nz_quantity for warehouse in item.warehouses), ZERO)


class _WarehouseSlot:
    def __init__(self, name: str) -> None:
        self.name = name
        self.total = ZERO


class _DepartmentBucket:
    def __init__(self, name: str) -> None:
        self.name = name
        self.warehouses: dict[int, _WarehouseSlot] = {}


async def get_nz_by_department(
    db: AsyncSession,
    *,
    unit: MassUnit = "т",
    department_id: UUID | None = None,
    warehouse_code: int | None = None,
) -> NzByDepartmentData:
    rows, unit = await _active_normative_rows(
        db,
        unit,
        department_id=department_id,
        warehouse_code=warehouse_code,
    )
    buckets: dict[UUID | None, _DepartmentBucket] = {}
    for (
        quantity,
        source_unit,
        row_warehouse_code,
        warehouse_name,
        weight_kg,
        _client_id,
        _code,
        _name,
        _inn,
        row_department_id,
        department_name,
    ) in rows:
        mass = to_mass(quantity, source_unit, weight_kg or ZERO, unit)
        bucket = buckets.setdefault(
            row_department_id,
            _DepartmentBucket(department_name or NO_DEPARTMENT),
        )
        slot = bucket.warehouses.setdefault(
            row_warehouse_code,
            _WarehouseSlot(str(warehouse_name)),
        )
        slot.total += mass
    items: list[NzByDepartmentItem] = []
    for row_department_id, bucket in buckets.items():
        warehouse_items = [
            NzByDepartmentWarehouse(
                warehouse_code=code,
                warehouse_name=slot.name,
                nz_quantity=_quantize_mass(slot.total, unit),
            )
            for code, slot in bucket.warehouses.items()
            if slot.total > 0
        ]
        warehouse_items.sort(key=lambda item: item.nz_quantity, reverse=True)
        if not warehouse_items:
            continue
        items.append(
            NzByDepartmentItem(
                department_id=row_department_id,
                department_name=bucket.name,
                warehouses=warehouse_items,
            )
        )
    items.sort(key=_department_total, reverse=True)
    return NzByDepartmentData(unit=unit, items=items)


async def get_top_clients(
    db: AsyncSession,
    *,
    unit: MassUnit = "т",
    limit: int = 10,
    department_id: UUID | None = None,
    warehouse_code: int | None = None,
) -> TopClientsData:
    rows, unit = await _active_normative_rows(
        db,
        unit,
        department_id=department_id,
        warehouse_code=warehouse_code,
    )
    buckets: dict[UUID, dict[str, object]] = {}
    for (
        quantity,
        source_unit,
        _warehouse_code,
        _warehouse_name,
        weight_kg,
        client_id,
        client_code,
        client_name,
        inn,
        _row_department_id,
        department_name,
    ) in rows:
        mass = to_mass(quantity, source_unit, weight_kg or ZERO, unit)
        bucket = buckets.setdefault(
            client_id,
            {
                "code": client_code,
                "name": client_name,
                "inn": inn,
                "department_name": department_name,
                "total": ZERO,
            },
        )
        bucket["total"] = Decimal(str(bucket["total"])) + mass
    ranked = sorted(
        (
            (client_id, bucket)
            for client_id, bucket in buckets.items()
            if Decimal(str(bucket["total"])) > 0
        ),
        key=lambda item: Decimal(str(item[1]["total"])),
        reverse=True,
    )
    visible = ranked[:limit]
    hidden = ranked[limit:]
    items = [
        TopClientItem(
            client_id=client_id,
            client_code=int(str(bucket["code"])),
            client_name=str(bucket["name"]),
            inn=str(bucket["inn"]),
            department_name=(
                str(bucket["department_name"])
                if bucket["department_name"] is not None
                else None
            ),
            nz_quantity=_quantize_mass(Decimal(str(bucket["total"])), unit),
            is_other=False,
        )
        for client_id, bucket in visible
    ]
    others_total = sum(
        (Decimal(str(bucket["total"])) for _client_id, bucket in hidden),
        ZERO,
    )
    if others_total > 0:
        items.append(
            TopClientItem(
                client_name=OTHERS_LABEL,
                nz_quantity=_quantize_mass(others_total, unit),
                is_other=True,
            )
        )
    return TopClientsData(unit=unit, items=items)
