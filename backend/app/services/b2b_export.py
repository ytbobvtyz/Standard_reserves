from decimal import ROUND_HALF_UP, Decimal
from io import BytesIO
from typing import Literal

from openpyxl import Workbook
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import APIError
from app.models.object import Object
from app.models.product import Product
from app.schemas.logistics import B2BRoute, B2BRouteItem

KG_IN_TON = Decimal("1000")
UNSAFE_FILENAME_CHARS = '<>:"/\\|?*'
B2BUnit = Literal["шт", "кг", "т"]


def normalize_b2b_unit(unit: str) -> B2BUnit:
    text = (unit or "").strip().lower().replace(".", "").replace(" ", "")
    if text in {"шт", "штук", "pcs"}:
        return "шт"
    if text in {"т", "t", "ton", "тонн", "тонна"}:
        return "т"
    return "кг"


def convert_to_kg(weight_kg: Decimal, deficit: Decimal, unit: str) -> Decimal:
    """Пересчёт дефицита в килограммы."""
    kind = normalize_b2b_unit(unit)
    if kind == "шт":
        kg = deficit * weight_kg
    elif kind == "т":
        kg = deficit * KG_IN_TON
    else:
        kg = deficit
    return kg.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _safe_filename(name: str) -> str:
    cleaned = "".join("-" if char in UNSAFE_FILENAME_CHARS else char for char in name)
    cleaned = " ".join(cleaned.split()).strip(" .")
    return cleaned or "route"


def route_excel_filename(plant_name: str, warehouse_name: str) -> str:
    return f"{_safe_filename(plant_name)} → {_safe_filename(warehouse_name)}.xlsx"


def generate_b2b_excel(rows: list[tuple[int, str, Decimal]]) -> bytes:
    """Excel B2B: Артикул | Наименование | Дефицит (кг)."""
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Разнарядка"
    sheet["A1"] = "Артикул"
    sheet["B1"] = "Наименование"
    sheet["C1"] = "Дефицит (кг)"
    for row_idx, (product_code, product_name, deficit_kg) in enumerate(rows, start=2):
        sheet[f"A{row_idx}"] = product_code
        sheet[f"B{row_idx}"] = product_name
        sheet[f"C{row_idx}"] = float(deficit_kg)
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _unique_filename(name: str, used: set[str]) -> str:
    if name not in used:
        return name
    stem, suffix = name.rsplit(".xlsx", 1)[0], ".xlsx"
    index = 2
    candidate = f"{stem} ({index}){suffix}"
    while candidate in used:
        index += 1
        candidate = f"{stem} ({index}){suffix}"
    return candidate


async def generate_b2b_exports(
    db: AsyncSession,
    routes: list[B2BRoute],
) -> dict[str, bytes]:
    if not routes:
        raise APIError(400, "VALIDATION_ERROR", "Укажите хотя бы один маршрут")

    product_codes = {item.product_code for route in routes for item in route.items}
    object_codes = {route.plant_code for route in routes} | {
        route.warehouse_code for route in routes
    }

    products: dict[int, Product] = {}
    if product_codes:
        result = await db.execute(
            select(Product).where(
                Product.code.in_(product_codes),
                Product.deleted_at.is_(None),
            )
        )
        products = {item.code: item for item in result.scalars().all()}

    objects: dict[int, Object] = {}
    if object_codes:
        result = await db.execute(
            select(Object).where(
                Object.code.in_(object_codes),
                Object.deleted_at.is_(None),
            )
        )
        objects = {item.code: item for item in result.scalars().all()}

    missing = sorted(code for code in product_codes if code not in products)
    if missing:
        raise APIError(
            400,
            "VALIDATION_ERROR",
            f"Продукт {missing[0]} не найден",
        )

    exports: dict[str, bytes] = {}
    used_names: set[str] = set()
    for route in routes:
        if not route.items:
            continue
        plant = objects.get(route.plant_code)
        warehouse = objects.get(route.warehouse_code)
        plant_name = route.plant_name.strip() or (
            plant.name if plant else str(route.plant_code)
        )
        warehouse_name = route.warehouse_name.strip() or (
            warehouse.name if warehouse else str(route.warehouse_code)
        )
        excel_rows: list[tuple[int, str, Decimal]] = []
        for item in route.items:
            excel_rows.append(_row_from_item(item, products[item.product_code]))
        filename = _unique_filename(
            route_excel_filename(plant_name, warehouse_name),
            used_names,
        )
        used_names.add(filename)
        exports[filename] = generate_b2b_excel(excel_rows)

    if not exports:
        raise APIError(400, "VALIDATION_ERROR", "Нет данных для выгрузки")
    return exports


def _row_from_item(item: B2BRouteItem, product: Product) -> tuple[int, str, Decimal]:
    deficit_kg = convert_to_kg(product.weight_kg, Decimal(str(item.deficit)), item.unit)
    return (product.code, product.name, deficit_kg)
