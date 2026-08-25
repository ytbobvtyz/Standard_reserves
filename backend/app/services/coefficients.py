from decimal import Decimal, localcontext

from app.models.object import Object
from app.models.product import Product
from app.services.logistics_normative import (
    calculate_requirement,
    category_factor,
    distance_factor,
)

REQUIREMENT_QUANT = Decimal("1e-32")


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
