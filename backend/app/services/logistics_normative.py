from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from io import BytesIO
from typing import Literal

from openpyxl import Workbook
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import APIError
from app.models.available_balance import AvailableBalance
from app.models.normative import Normative
from app.models.object import Object
from app.models.product import Product
from app.schemas.logistics import (
    DashboardResponse,
    DashboardSummary,
    DeficitItem,
    FilterMode,
    GenerateOrdersData,
    OrderItem,
    PlantOrder,
    Unit,
    WarehouseDeficit,
)

ESTIMATED_DELIVERY_DAYS = 5
KG_IN_TON = Decimal("1000")


@dataclass
class DeficitRow:
    warehouse_code: int
    warehouse_name: str
    product_code: int
    product_name: str
    category: str
    plant_id: int
    second_plant_id: int | None
    third_plant_id: int | None
    plant_name: str
    weight_kg: Decimal
    normative_quantity: Decimal
    fact_quantity: Decimal
    deficit: Decimal
    unit: str
    client_name: str
    expiry_date: date | None
    status: Literal["warning", "ok"]


def _quantize(value: Decimal, unit: Unit) -> Decimal:
    step = Decimal("0.0001") if unit == "т" else Decimal("0.01")
    return value.quantize(step, rounding=ROUND_HALF_UP)


def to_pieces(quantity: Decimal, unit: str, weight_kg: Decimal) -> Decimal:
    if unit == "шт":
        return quantity
    if weight_kg <= 0:
        return Decimal("0")
    return quantity * KG_IN_TON / weight_kg


def from_pieces(quantity: Decimal, unit: Unit, weight_kg: Decimal) -> Decimal:
    if unit == "шт":
        return quantity
    return quantity * weight_kg / KG_IN_TON


def resolve_plant_id(product: Product) -> int:
    for code in (product.plant_id, product.second_plant_id, product.third_plant_id):
        if code:
            return code
    return product.plant_id


def _item_key(warehouse_code: int, product_code: int) -> tuple[int, int]:
    return (warehouse_code, product_code)


def _convert_row(
    *,
    warehouse: Object,
    product: Product,
    plant_name: str,
    normative_pcs: Decimal,
    fact_pcs: Decimal,
    unit: Unit,
    client_name: str,
    expiry_date: date | None,
) -> DeficitRow:
    deficit_pcs = normative_pcs - fact_pcs
    status: Literal["warning", "ok"] = "warning" if deficit_pcs > 0 else "ok"
    return DeficitRow(
        warehouse_code=warehouse.code,
        warehouse_name=warehouse.name,
        product_code=product.code,
        product_name=product.name,
        category=product.category.strip(),
        plant_id=resolve_plant_id(product),
        second_plant_id=product.second_plant_id,
        third_plant_id=product.third_plant_id,
        plant_name=plant_name,
        weight_kg=product.weight_kg,
        normative_quantity=_quantize(
            from_pieces(normative_pcs, unit, product.weight_kg), unit
        ),
        fact_quantity=_quantize(from_pieces(fact_pcs, unit, product.weight_kg), unit),
        deficit=_quantize(from_pieces(deficit_pcs, unit, product.weight_kg), unit),
        unit=unit,
        client_name=client_name,
        expiry_date=expiry_date,
        status=status,
    )


async def _load_plants(db: AsyncSession, plant_ids: set[int]) -> dict[int, Object]:
    if not plant_ids:
        return {}
    result = await db.execute(select(Object).where(Object.code.in_(plant_ids)))
    return {item.code: item for item in result.scalars().all()}


async def collect_deficit_rows(
    db: AsyncSession,
    *,
    warehouse_code: int | None = None,
    filter_mode: FilterMode = "with_normatives",
    unit: Unit = "шт",
    product_codes: list[int] | None = None,
) -> list[DeficitRow]:
    today = date.today()
    conditions = [
        Normative.deleted_at.is_(None),
        Normative.expiry_date >= today,
        Product.deleted_at.is_(None),
        Object.deleted_at.is_(None),
    ]
    if warehouse_code is not None:
        conditions.append(Normative.warehouse_code == warehouse_code)
    if product_codes:
        conditions.append(Normative.product_code.in_(product_codes))

    result = await db.execute(
        select(Normative)
        .options(
            selectinload(Normative.product).selectinload(Product.plant),
            selectinload(Normative.warehouse),
        )
        .join(Product, Product.code == Normative.product_code)
        .join(Object, Object.code == Normative.warehouse_code)
        .where(*conditions)
        .order_by(Normative.warehouse_code, Normative.product_code)
    )
    normatives = list(result.scalars().unique().all())

    balance_conditions = []
    if warehouse_code is not None:
        balance_conditions.append(AvailableBalance.warehouse_code == warehouse_code)
    if product_codes:
        balance_conditions.append(AvailableBalance.product_code.in_(product_codes))
    balance_stmt = select(AvailableBalance)
    if balance_conditions:
        balance_stmt = balance_stmt.where(*balance_conditions)
    balances = {
        (item.warehouse_code, item.product_code): item
        for item in (await db.execute(balance_stmt)).scalars().all()
    }

    aggregated: dict[tuple[int, int], dict] = {}
    for normative in normatives:
        product = normative.product
        key = _item_key(normative.warehouse_code, normative.product_code)
        bucket = aggregated.setdefault(
            key,
            {
                "warehouse": normative.warehouse,
                "product": product,
                "normative_pcs": Decimal("0"),
                "clients": [],
                "expiry_date": normative.expiry_date,
            },
        )
        bucket["normative_pcs"] += to_pieces(
            normative.quantity, normative.unit, product.weight_kg
        )
        if normative.client_name and normative.client_name not in bucket["clients"]:
            bucket["clients"].append(normative.client_name)
        if (
            bucket["expiry_date"] is None
            or normative.expiry_date < bucket["expiry_date"]
        ):
            bucket["expiry_date"] = normative.expiry_date

    covered_keys = set(aggregated)
    if filter_mode == "all":
        extra_keys = [key for key in balances if key not in covered_keys]
        extra_product_codes = {product_code for _, product_code in extra_keys}
        extra_warehouse_codes = {wh for wh, _ in extra_keys}
        products_by_code: dict[int, Product] = {}
        warehouses_by_code: dict[int, Object] = {}
        if extra_product_codes:
            products_by_code = {
                item.code: item
                for item in (
                    await db.execute(
                        select(Product)
                        .options(selectinload(Product.plant))
                        .where(
                            Product.code.in_(extra_product_codes),
                            Product.deleted_at.is_(None),
                        )
                    )
                )
                .scalars()
                .all()
            }
        if extra_warehouse_codes:
            warehouses_by_code = {
                item.code: item
                for item in (
                    await db.execute(
                        select(Object).where(
                            Object.code.in_(extra_warehouse_codes),
                            Object.deleted_at.is_(None),
                        )
                    )
                )
                .scalars()
                .all()
            }
        for warehouse_code_key, product_code in extra_keys:
            product = products_by_code.get(product_code)
            warehouse = warehouses_by_code.get(warehouse_code_key)
            if product is None or warehouse is None:
                continue
            aggregated[(warehouse_code_key, product_code)] = {
                "warehouse": warehouse,
                "product": product,
                "normative_pcs": Decimal("0"),
                "clients": [],
                "expiry_date": None,
            }

    plant_ids = {resolve_plant_id(bucket["product"]) for bucket in aggregated.values()}
    plants = await _load_plants(db, plant_ids)

    rows: list[DeficitRow] = []
    for warehouse_code_key, product_code in sorted(aggregated):
        bucket = aggregated[(warehouse_code_key, product_code)]
        product: Product = bucket["product"]
        warehouse: Object = bucket["warehouse"]
        balance = balances.get((warehouse_code_key, product_code))
        fact_pcs = (
            to_pieces(balance.quantity, balance.unit, product.weight_kg)
            if balance is not None
            else Decimal("0")
        )
        plant = plants.get(resolve_plant_id(product))
        row = _convert_row(
            warehouse=warehouse,
            product=product,
            plant_name=plant.name if plant else f"Завод {resolve_plant_id(product)}",
            normative_pcs=bucket["normative_pcs"],
            fact_pcs=fact_pcs,
            unit=unit,
            client_name=", ".join(bucket["clients"]),
            expiry_date=bucket["expiry_date"],
        )
        if filter_mode == "deficit_only" and row.deficit <= 0:
            continue
        if filter_mode == "with_normatives" and bucket["normative_pcs"] <= 0:
            continue
        rows.append(row)
    return rows


def _to_deficit_item(row: DeficitRow) -> DeficitItem:
    return DeficitItem(
        product_code=row.product_code,
        product_name=row.product_name,
        category=row.category,
        normative_quantity=row.normative_quantity,
        fact_quantity=row.fact_quantity,
        unit=row.unit,
        deficit=row.deficit,
        client_name=row.client_name,
        expiry_date=row.expiry_date,
        status=row.status,
    )


def build_dashboard(rows: list[DeficitRow]) -> DashboardResponse:
    grouped: dict[int, list[DeficitRow]] = defaultdict(list)
    names: dict[int, str] = {}
    for row in rows:
        grouped[row.warehouse_code].append(row)
        names[row.warehouse_code] = row.warehouse_name

    warehouses: list[WarehouseDeficit] = []
    for warehouse_code in sorted(grouped):
        items = grouped[warehouse_code]
        positive = [item for item in items if item.deficit > 0]
        total = sum((item.deficit for item in positive), Decimal("0"))
        warehouses.append(
            WarehouseDeficit(
                warehouse_code=warehouse_code,
                warehouse_name=names[warehouse_code],
                deficit_items=[_to_deficit_item(item) for item in items],
                total_deficit=total,
                deficit_count=len(positive),
            )
        )

    positive_rows = [row for row in rows if row.deficit > 0]
    return DashboardResponse(
        data=warehouses,
        summary=DashboardSummary(
            total_deficit=sum((row.deficit for row in positive_rows), Decimal("0")),
            deficit_warehouses=len({row.warehouse_code for row in positive_rows}),
            deficit_products=len({row.product_code for row in positive_rows}),
        ),
    )


async def get_dashboard(
    db: AsyncSession,
    *,
    warehouse_code: int | None = None,
    filter_mode: FilterMode = "with_normatives",
    unit: Unit = "шт",
) -> DashboardResponse:
    rows = await collect_deficit_rows(
        db,
        warehouse_code=warehouse_code,
        filter_mode=filter_mode,
        unit=unit,
    )
    return build_dashboard(rows)


def _orders_payload(orders: list[PlantOrder]) -> GenerateOrdersData:
    product_codes_count = {item.product_code for row in orders for item in row.items}
    total_quantity = sum(
        (item.deficit for row in orders for item in row.items),
        Decimal("0"),
    )
    return GenerateOrdersData(
        orders=orders,
        total_orders=len(orders),
        total_products=len(product_codes_count),
        total_quantity=total_quantity,
    )


async def _get_warehouse(db: AsyncSession, warehouse_code: int) -> Object:
    warehouse = await db.get(Object, warehouse_code)
    if (
        warehouse is None
        or warehouse.deleted_at is not None
        or warehouse.type != "warehouse"
    ):
        raise APIError(404, "NOT_FOUND", "Склад не найден")
    return warehouse


async def generate_orders(
    db: AsyncSession,
    *,
    warehouse_code: int,
    product_codes: list[int] | None = None,
) -> GenerateOrdersData:
    warehouse = await _get_warehouse(db, warehouse_code)

    rows = await collect_deficit_rows(
        db,
        warehouse_code=warehouse_code,
        filter_mode="deficit_only",
        unit="шт",
        product_codes=product_codes,
    )
    grouped: dict[int, list[DeficitRow]] = defaultdict(list)
    for row in rows:
        if row.deficit <= 0:
            continue
        grouped[row.plant_id].append(row)

    plant_ids = set(grouped)
    plants = await _load_plants(db, plant_ids)
    orders: list[PlantOrder] = []
    for plant_code in sorted(grouped):
        plant = plants.get(plant_code)
        items = grouped[plant_code]
        orders.append(
            PlantOrder(
                plant_code=plant_code,
                plant_name=plant.name if plant else items[0].plant_name,
                warehouse_code=warehouse.code,
                warehouse_name=warehouse.name,
                items=[
                    OrderItem(
                        product_code=item.product_code,
                        product_name=item.product_name,
                        deficit=item.deficit,
                        unit=item.unit,
                    )
                    for item in items
                ],
                estimated_delivery_days=ESTIMATED_DELIVERY_DAYS,
            )
        )

    return _orders_payload(orders)


async def generate_orders_for_warehouses(
    db: AsyncSession,
    *,
    warehouse_codes: list[int],
    product_codes: list[int] | None = None,
) -> GenerateOrdersData:
    if not warehouse_codes:
        raise APIError(400, "VALIDATION_ERROR", "Укажите хотя бы один склад")

    unique_codes = list(dict.fromkeys(warehouse_codes))
    for code in unique_codes:
        await _get_warehouse(db, code)

    orders: list[PlantOrder] = []
    for code in unique_codes:
        result = await generate_orders(
            db,
            warehouse_code=code,
            product_codes=product_codes,
        )
        orders.extend(result.orders)
    return _orders_payload(orders)


async def export_excel(
    db: AsyncSession,
    *,
    warehouse_code: int | None = None,
    product_codes: list[int] | None = None,
    unit: Unit = "шт",
) -> bytes:
    rows = await collect_deficit_rows(
        db,
        warehouse_code=warehouse_code,
        filter_mode="deficit_only",
        unit=unit,
        product_codes=product_codes,
    )
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Дефицит"
    sheet.append(
        ["Склад", "Артикул", "Название", "Норматив", "Факт", "Дефицит", "Ед", "Клиент"]
    )
    for row in rows:
        sheet.append(
            [
                row.warehouse_name,
                row.product_code,
                row.product_name,
                float(row.normative_quantity),
                float(row.fact_quantity),
                float(row.deficit),
                row.unit,
                row.client_name,
            ]
        )
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
