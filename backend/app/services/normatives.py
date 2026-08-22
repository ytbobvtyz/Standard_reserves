from collections import defaultdict
from datetime import UTC, date, datetime, time
from decimal import Decimal
from typing import Literal

from sqlalchemy import String, cast, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import APIError
from app.core.pagination import paginate
from app.models.normative import Normative
from app.models.object import Object
from app.models.product import Product
from app.schemas.common import PaginationMeta
from app.schemas.normative import (
    NormativeCalculateData,
    NormativeListItem,
    NormativeOnDateDetail,
    NormativeOnDateItem,
)

DISTANCE_FACTOR = Decimal("1")
CATEGORY_FACTORS = {
    "A": Decimal("1"),
    "B": Decimal("1.5"),
    "C": Decimal("2"),
}
DEFAULT_UNIT = "шт"

CategoryFilter = Literal["A", "B", "C"]


def _end_of_day(value: date) -> datetime:
    return datetime.combine(value, time.max, tzinfo=UTC)


def _product_search_condition(search: str | None):
    if not search or not search.strip():
        return None
    term = f"%{search.strip()}%"
    return exists(
        select(1).where(
            Product.code == Normative.product_code,
            or_(
                cast(Product.code, String).ilike(term),
                Product.name.ilike(term),
            ),
        )
    )


def to_list_item(normative: Normative) -> NormativeListItem:
    return NormativeListItem(
        id=normative.id,
        product_code=normative.product_code,
        product_name=normative.product.name if normative.product else "",
        category=normative.category.strip(),
        warehouse_code=normative.warehouse_code,
        warehouse_name=normative.warehouse.name if normative.warehouse else "",
        quantity=normative.quantity,
        unit=normative.unit,
        client_name=normative.client_name,
        expiry_date=normative.expiry_date,
        created_at=normative.created_at,
    )


async def list_current_normatives(
    db: AsyncSession,
    *,
    warehouse_code: int | None,
    product_code: int | None,
    client_name: str | None,
    category: CategoryFilter | None,
    search: str | None,
    page: int,
    limit: int,
) -> tuple[list[NormativeListItem], PaginationMeta]:
    conditions = [
        Normative.deleted_at.is_(None),
        Normative.expiry_date >= date.today(),
    ]
    if warehouse_code is not None:
        conditions.append(Normative.warehouse_code == warehouse_code)
    if product_code is not None:
        conditions.append(Normative.product_code == product_code)
    if client_name:
        conditions.append(Normative.client_name.ilike(f"%{client_name.strip()}%"))
    if category:
        conditions.append(Normative.category == category)
    search_condition = _product_search_condition(search)
    if search_condition is not None:
        conditions.append(search_condition)

    total = await db.scalar(
        select(func.count()).select_from(Normative).where(*conditions)
    )
    result = await db.execute(
        paginate(
            select(Normative)
            .options(
                selectinload(Normative.product),
                selectinload(Normative.warehouse),
            )
            .where(*conditions)
            .order_by(
                Normative.warehouse_code,
                Normative.product_code,
                Normative.created_at.desc(),
            ),
            page,
            limit,
        )
    )
    items = [to_list_item(row) for row in result.scalars().unique().all()]
    return items, PaginationMeta(page=page, limit=limit, total=total or 0)


async def list_normatives_on_date(
    db: AsyncSession,
    *,
    on_date: date,
    warehouse_code: int | None,
    product_code: int | None,
    search: str | None = None,
) -> list[NormativeOnDateItem]:
    conditions = [
        Normative.created_at <= _end_of_day(on_date),
        Normative.expiry_date >= on_date,
    ]
    if warehouse_code is not None:
        conditions.append(Normative.warehouse_code == warehouse_code)
    if product_code is not None:
        conditions.append(Normative.product_code == product_code)
    search_condition = _product_search_condition(search)
    if search_condition is not None:
        conditions.append(search_condition)

    result = await db.execute(
        select(Normative)
        .options(
            selectinload(Normative.product),
            selectinload(Normative.warehouse),
        )
        .where(*conditions)
        .order_by(
            Normative.warehouse_code,
            Normative.product_code,
            Normative.client_name,
        )
    )
    grouped: dict[tuple[int, int, str], list[Normative]] = defaultdict(list)
    for normative in result.scalars().unique().all():
        key = (normative.warehouse_code, normative.product_code, normative.unit)
        grouped[key].append(normative)

    items: list[NormativeOnDateItem] = []
    for (_warehouse, _product, unit), rows in grouped.items():
        first = rows[0]
        items.append(
            NormativeOnDateItem(
                product_code=first.product_code,
                product_name=first.product.name if first.product else "",
                warehouse_code=first.warehouse_code,
                warehouse_name=first.warehouse.name if first.warehouse else "",
                total_quantity=sum((row.quantity for row in rows), Decimal("0")),
                unit=unit,
                category=first.category.strip(),
                details=[
                    NormativeOnDateDetail(
                        client_name=row.client_name,
                        quantity=row.quantity,
                        expiry_date=row.expiry_date,
                    )
                    for row in rows
                ],
            )
        )
    items.sort(key=lambda item: (item.warehouse_code, item.product_code))
    return items


async def calculate_normative(
    db: AsyncSession,
    *,
    product_code: int,
    warehouse_code: int,
) -> NormativeCalculateData:
    product = await db.scalar(
        select(Product).where(
            Product.code == product_code,
            Product.deleted_at.is_(None),
        )
    )
    if product is None:
        raise APIError(404, "NOT_FOUND", "Продукт не найден")

    warehouse = await db.scalar(
        select(Object).where(
            Object.code == warehouse_code,
            Object.deleted_at.is_(None),
        )
    )
    if warehouse is None:
        raise APIError(404, "NOT_FOUND", "Склад не найден")

    category = product.category.strip()
    category_factor = CATEGORY_FACTORS.get(category, Decimal("1"))
    monthly = product.monthly_consumption
    calculated = None
    if monthly is not None:
        calculated = monthly * DISTANCE_FACTOR * category_factor

    return NormativeCalculateData(
        product_code=product.code,
        product_name=product.name,
        category=category,
        warehouse_code=warehouse.code,
        warehouse_name=warehouse.name,
        monthly_consumption=monthly,
        distance_factor=DISTANCE_FACTOR,
        category_factor=category_factor,
        calculated_normative=calculated,
        unit=DEFAULT_UNIT,
    )
