from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import DecimalNumber

FilterMode = Literal["all", "with_normatives", "deficit_only"]
Unit = Literal["шт", "т"]


class GenerateOrdersRequest(BaseModel):
    product_codes: list[int] | None = None


class DeficitItem(BaseModel):
    product_code: int
    product_name: str
    category: str
    normative_quantity: DecimalNumber
    fact_quantity: DecimalNumber
    unit: str
    deficit: DecimalNumber
    client_name: str
    expiry_date: date | None = None
    status: Literal["warning", "ok"]


class WarehouseDeficit(BaseModel):
    warehouse_code: int
    warehouse_name: str
    deficit_items: list[DeficitItem]
    total_deficit: DecimalNumber
    deficit_count: int


class DashboardSummary(BaseModel):
    total_deficit: DecimalNumber
    deficit_warehouses: int
    deficit_products: int


class DashboardResponse(BaseModel):
    status: str = Field(default="success")
    data: list[WarehouseDeficit]
    summary: DashboardSummary


class OrderItem(BaseModel):
    product_code: int
    product_name: str
    deficit: DecimalNumber
    unit: str


class PlantOrder(BaseModel):
    plant_code: int
    plant_name: str
    warehouse_code: int
    warehouse_name: str
    items: list[OrderItem]
    estimated_delivery_days: int = 5


class GenerateOrdersData(BaseModel):
    orders: list[PlantOrder]
    total_orders: int
    total_products: int
    total_quantity: DecimalNumber
