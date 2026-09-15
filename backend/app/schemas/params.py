from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import DecimalNumber

COEFF_STEP = Decimal("0.1")
COEFF_MIN = Decimal("1")
COEFF_MAX = Decimal("3")


def validate_coefficient(value: Decimal) -> Decimal:
    quantized = Decimal(str(value)).quantize(COEFF_STEP)
    scaled = Decimal(str(value)) * 10
    if abs(scaled - scaled.to_integral_value()) > Decimal("0.0000001"):
        raise ValueError("Коэффициент должен быть от 1 до 3 с шагом 0,1")
    if quantized < COEFF_MIN or quantized > COEFF_MAX:
        raise ValueError("Коэффициент должен быть от 1 до 3 с шагом 0,1")
    return quantized


class ParamsLastModifiedBy(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    full_name: str


class ParamsResponse(BaseModel):
    category_a: DecimalNumber
    category_b: DecimalNumber
    category_c: DecimalNumber
    remote_warehouse: DecimalNumber
    pallet_multiple: bool
    last_modified_by: ParamsLastModifiedBy | None = None
    last_modified_at: datetime | None = None


class ParamsUpdate(BaseModel):
    category_a: Decimal = Field(...)
    category_b: Decimal = Field(...)
    category_c: Decimal = Field(...)
    remote_warehouse: Decimal = Field(...)
    pallet_multiple: bool

    @field_validator(
        "category_a", "category_b", "category_c", "remote_warehouse"
    )
    @classmethod
    def check_coefficient(cls, value: Decimal) -> Decimal:
        return validate_coefficient(value)
