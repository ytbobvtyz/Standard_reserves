from dataclasses import dataclass
from decimal import Decimal, localcontext

from app.models.object import Object
from app.models.product import Product

REQUIREMENT_QUANT = Decimal("1e-32")
NEAR_DISTANCE_FACTOR = Decimal("1")


@dataclass(frozen=True)
class CoefficientSet:
    category_a: Decimal = Decimal("1")
    category_b: Decimal = Decimal("1.5")
    category_c: Decimal = Decimal("2")
    remote_warehouse: Decimal = Decimal("1.5")

    def category_factor(self, category: str) -> Decimal:
        key = category.strip().upper()
        mapping = {
            "A": self.category_a,
            "B": self.category_b,
            "C": self.category_c,
        }
        return mapping.get(key, Decimal("1"))

    def distance_factor(self, long_distance: bool) -> Decimal:
        return self.remote_warehouse if long_distance else NEAR_DISTANCE_FACTOR


DEFAULT_COEFFICIENTS = CoefficientSet()
CATEGORY_FACTORS = {
    "A": DEFAULT_COEFFICIENTS.category_a,
    "B": DEFAULT_COEFFICIENTS.category_b,
    "C": DEFAULT_COEFFICIENTS.category_c,
}
DISTANCE_FACTOR_REMOTE = DEFAULT_COEFFICIENTS.remote_warehouse
DISTANCE_FACTOR_NEAR = NEAR_DISTANCE_FACTOR


def category_factor(
    category: str, coeffs: CoefficientSet | None = None
) -> Decimal:
    return (coeffs or DEFAULT_COEFFICIENTS).category_factor(category)


def distance_factor(
    long_distance: bool, coeffs: CoefficientSet | None = None
) -> Decimal:
    return (coeffs or DEFAULT_COEFFICIENTS).distance_factor(long_distance)


def calculate_requirement(
    normative_quantity: Decimal,
    category: str,
    long_distance: bool,
    coeffs: CoefficientSet | None = None,
) -> Decimal:
    active = coeffs or DEFAULT_COEFFICIENTS
    return (
        normative_quantity
        * active.category_factor(category)
        * active.distance_factor(long_distance)
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
    coeffs: CoefficientSet | None = None,
) -> dict:
    active = coeffs or DEFAULT_COEFFICIENTS
    category = (product.category or "A").strip()
    long_distance = bool(warehouse.long_distance)
    return {
        "category": category,
        "category_factor": active.category_factor(category),
        "long_distance": long_distance,
        "distance_factor": active.distance_factor(long_distance),
        "requirement": round_requirement(
            calculate_requirement(quantity, category, long_distance, active)
        ),
    }
