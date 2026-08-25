from decimal import Decimal, localcontext

from app.models.object import Object
from app.models.product import Product

CATEGORY_FACTORS = {
    "A": Decimal("1"),
    "B": Decimal("1.5"),
    "C": Decimal("2"),
}
DISTANCE_FACTOR_REMOTE = Decimal("1.5")
DISTANCE_FACTOR_NEAR = Decimal("1")
REQUIREMENT_QUANT = Decimal("1e-32")


def category_factor(category: str) -> Decimal:
    return CATEGORY_FACTORS.get(category.strip().upper(), Decimal("1"))


def distance_factor(long_distance: bool) -> Decimal:
    return DISTANCE_FACTOR_REMOTE if long_distance else DISTANCE_FACTOR_NEAR


def calculate_requirement(
    normative_quantity: Decimal,
    category: str,
    long_distance: bool,
) -> Decimal:
    return (
        normative_quantity * category_factor(category) * distance_factor(long_distance)
    )


def round_requirement(value: Decimal) -> Decimal:
    integer_digits = max(value.adjusted() + 1, 1)
    with localcontext() as context:
        context.prec = max(64, integer_digits + 32)
        return value.quantize(REQUIREMENT_QUANT)


def item_coefficient_fields(
    product: Product,
    warehouse: Object,
    quantity: Decimal,
) -> dict:
    category = (product.category or "A").strip()
    long_distance = bool(warehouse.long_distance)
    return {
        "category": category,
        "category_factor": category_factor(category),
        "long_distance": long_distance,
        "distance_factor": distance_factor(long_distance),
        "requirement": round_requirement(
            calculate_requirement(quantity, category, long_distance)
        ),
    }
