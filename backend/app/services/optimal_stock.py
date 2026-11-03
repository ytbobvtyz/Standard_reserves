"""Monthly sales average for a normative request."""

from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import APIError
from app.models.actual_shipment import ActualShipment
from app.models.normative import Normative
from app.models.object import Object
from app.models.product import Product
from app.models.user import User
from app.schemas.optimal import (
    OptimalCalculateData,
    OptimalCalculatedItem,
    OptimalCalculateRequest,
    OptimalExistingNormative,
    OptimalSkippedItem,
)
from app.services.clients import require_client
from app.services.normative_dates import commercial_active_on
from app.services.requests import can_create_request

MONTHS_IN_WINDOW = 6
MIN_MONTH_KG = Decimal("1")
KG_IN_TON = Decimal("1000")
QUANTITY_QUANT = Decimal("0.01")
REASON_NO_SALES = "Нет реализации"
REASON_BELOW_PALLET = "Реализация меньше 1 паллеты"
REASON_UNMAPPED = "Пункт отгрузки не найден среди складов"
REASON_INACTIVE = "Продукт неактивен"
REASON_UNKNOWN_PRODUCT = "Продукт не найден"


def previous_month_starts(today: date, count: int = MONTHS_IN_WINDOW) -> list[date]:
    """First days of previous calendar months, oldest first. Current month is out."""
    year = today.year
    month = today.month
    starts: list[date] = []
    for _ in range(count):
        month -= 1
        if month == 0:
            year -= 1
            month = 12
        starts.append(date(year, month, 1))
    starts.reverse()
    return starts


def _month_after(start: date) -> date:
    if start.month == 12:
        return date(start.year + 1, 1, 1)
    return date(start.year, start.month + 1, 1)


def month_index(shipment_date: date, starts: list[date]) -> int | None:
    if not starts or shipment_date < starts[0]:
        return None
    current_start = _month_after(starts[-1])
    if shipment_date >= current_start:
        return None
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else current_start
        if start <= shipment_date < end:
            return index
    return None


def shipment_to_kg(quantity: Decimal, unit: str, weight_kg: Decimal | None) -> Decimal:
    if unit == "кг":
        return quantity
    if unit == "т":
        return quantity * KG_IN_TON
    weight = weight_kg or Decimal("0")
    if weight <= 0:
        return Decimal("0")
    return quantity * weight


def average_monthly_kg(monthly_kg: list[Decimal]) -> tuple[Decimal, int] | None:
    """Sum from the first month with at least 1 kg, divided by months in that tail."""
    first = next(
        (index for index, value in enumerate(monthly_kg) if value >= MIN_MONTH_KG),
        None,
    )
    if first is None:
        return None
    window = monthly_kg[first:]
    total = sum(window, Decimal("0"))
    months_used = len(window)
    average = (total / Decimal(months_used)).quantize(
        QUANTITY_QUANT,
        rounding=ROUND_HALF_UP,
    )
    return average, months_used


def pallet_threshold_kg(
    pallet_qty: int | None,
    weight_kg: Decimal | None,
) -> Decimal | None:
    if pallet_qty is None or pallet_qty < 1:
        return None
    if weight_kg is None or weight_kg <= 0:
        return None
    return Decimal(pallet_qty) * weight_kg


def _as_utc_date(value: datetime) -> date:
    if value.tzinfo is not None:
        return value.astimezone(UTC).date()
    return value.date()


async def calculate_optimal(
    db: AsyncSession,
    user: User,
    body: OptimalCalculateRequest,
    *,
    today: date | None = None,
) -> OptimalCalculateData:
    if not can_create_request(user, "normative"):
        raise APIError(403, "FORBIDDEN", "Недостаточно прав")

    client = await require_client(db, body.client_id)
    reference = today or date.today()
    starts = previous_month_starts(reference)
    window_start = starts[0]
    current_month_start = _month_after(starts[-1])

    shipments = (
        await db.scalars(
            select(ActualShipment).where(
                ActualShipment.client_id == client.id,
                ActualShipment.deleted_at.is_(None),
                ActualShipment.shipment_date >= window_start,
                ActualShipment.shipment_date < current_month_start,
            )
        )
    ).all()

    product_codes = {row.product_code for row in shipments}
    products: dict[int, Product] = {}
    if product_codes:
        products = {
            product.code: product
            for product in (
                await db.scalars(
                    select(Product).where(
                        Product.code.in_(product_codes),
                        Product.deleted_at.is_(None),
                    )
                )
            ).all()
        }
    points = {row.loading_point for row in shipments if row.loading_point}
    warehouses: dict[str, Object] = {}
    if points:
        warehouses = {
            warehouse.loading_point: warehouse
            for warehouse in (
                await db.scalars(
                    select(Object).where(
                        Object.loading_point.in_(points),
                        Object.type == "warehouse",
                        Object.is_active.is_(True),
                        Object.deleted_at.is_(None),
                    )
                )
            ).all()
            if warehouse.loading_point
        }

    monthly: dict[tuple[int, str], list[Decimal]] = {}
    for row in shipments:
        index = month_index(row.shipment_date, starts)
        if index is None:
            continue
        key = (row.product_code, row.loading_point)
        bucket = monthly.setdefault(key, [Decimal("0")] * MONTHS_IN_WINDOW)
        product = products.get(row.product_code)
        weight = None if product is None else product.weight_kg
        bucket[index] += shipment_to_kg(row.quantity, row.unit, weight)

    calculated: list[OptimalCalculatedItem] = []
    skipped: list[OptimalSkippedItem] = []
    for product_code, point in sorted(monthly):
        product = products.get(product_code)
        warehouse = warehouses.get(point)
        product_name = product.name if product is not None else ""
        warehouse_name = warehouse.name if warehouse is not None else point
        warehouse_code = warehouse.code if warehouse is not None else None
        if warehouse is None:
            skipped.append(
                OptimalSkippedItem(
                    product_code=product_code,
                    warehouse_code=None,
                    product_name=product_name,
                    warehouse_name=warehouse_name,
                    reason=REASON_UNMAPPED,
                )
            )
            continue
        if product is None:
            skipped.append(
                OptimalSkippedItem(
                    product_code=product_code,
                    warehouse_code=warehouse_code,
                    product_name=product_name,
                    warehouse_name=warehouse_name,
                    reason=REASON_UNKNOWN_PRODUCT,
                )
            )
            continue
        if not product.is_active:
            skipped.append(
                OptimalSkippedItem(
                    product_code=product_code,
                    warehouse_code=warehouse_code,
                    product_name=product_name,
                    warehouse_name=warehouse_name,
                    reason=REASON_INACTIVE,
                )
            )
            continue
        series = monthly[(product_code, point)]
        averaged = average_monthly_kg(series)
        if averaged is None:
            skipped.append(
                OptimalSkippedItem(
                    product_code=product_code,
                    warehouse_code=warehouse_code,
                    product_name=product_name,
                    warehouse_name=warehouse_name,
                    reason=REASON_NO_SALES,
                )
            )
            continue
        average, months_used = averaged
        total = sum(series, Decimal("0"))
        threshold = pallet_threshold_kg(product.pallet_qty, product.weight_kg)
        if threshold is not None and total < threshold:
            skipped.append(
                OptimalSkippedItem(
                    product_code=product_code,
                    warehouse_code=warehouse_code,
                    product_name=product_name,
                    warehouse_name=warehouse_name,
                    reason=REASON_BELOW_PALLET,
                )
            )
            continue
        calculated.append(
            OptimalCalculatedItem(
                product_code=product_code,
                warehouse_code=warehouse.code,
                product_name=product.name,
                warehouse_name=warehouse.name,
                category=product.category.strip(),
                weight_kg=product.weight_kg,
                pallet_qty=product.pallet_qty,
                calculated_quantity=average,
                months_used=months_used,
            )
        )

    existing_rows = (
        await db.scalars(
            select(Normative)
            .options(selectinload(Normative.product))
            .where(
                Normative.client_id == client.id,
                Normative.deleted_at.is_(None),
                Normative.expiry_date >= reference,
                commercial_active_on(reference),
            )
            .order_by(Normative.created_at.desc())
        )
    ).all()
    existing = [
        OptimalExistingNormative(
            id=row.id,
            request_id=row.request_id,
            created_at=_as_utc_date(row.created_at),
            client_name=row.client_name,
            quantity=row.quantity,
            unit=row.unit,
            expiry_date=row.expiry_date,
            product_code=row.product_code,
            product_name=row.product.name if row.product is not None else "",
        )
        for row in existing_rows
    ]
    return OptimalCalculateData(
        client_name=client.name,
        items=calculated,
        existing_normatives=existing,
        skipped_items=skipped,
    )
