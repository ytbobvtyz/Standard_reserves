from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import DecimalNumber


class OptimalCalculateItem(BaseModel):
    product_code: int
    warehouse_code: int


class OptimalCalculateRequest(BaseModel):
    client_id: UUID
    items: list[OptimalCalculateItem] = Field(default_factory=list)


class OptimalCalculatedItem(BaseModel):
    product_code: int
    warehouse_code: int
    product_name: str
    warehouse_name: str
    category: str
    weight_kg: DecimalNumber
    pallet_qty: int | None = None
    calculated_quantity: DecimalNumber
    unit: Literal["кг"] = "кг"
    months_used: int


class OptimalExistingNormative(BaseModel):
    id: UUID
    request_id: UUID | None = None
    created_at: date
    client_name: str
    quantity: DecimalNumber
    unit: str
    expiry_date: date
    product_code: int
    product_name: str


class OptimalSkippedItem(BaseModel):
    product_code: int
    warehouse_code: int | None = None
    product_name: str
    warehouse_name: str
    reason: str


class OptimalCalculateData(BaseModel):
    client_name: str
    items: list[OptimalCalculatedItem]
    existing_normatives: list[OptimalExistingNormative]
    skipped_items: list[OptimalSkippedItem]
