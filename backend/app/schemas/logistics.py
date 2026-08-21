from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import DecimalNumber
from app.schemas.user import UserBrief

FilterMode = Literal["all", "with_normatives", "deficit_only"]
Unit = Literal["шт", "т"]


class GenerateOrdersRequest(BaseModel):
    product_codes: list[int] | None = None


class GenerateOrdersBulkRequest(BaseModel):
    warehouse_codes: list[int] = Field(default_factory=list)
    product_codes: list[int] | None = None


class DeficitItem(BaseModel):
    product_code: int
    product_name: str
    category: str
    normative_quantity: DecimalNumber
    available: DecimalNumber
    plan: DecimalNumber
    unit: str
    deficit: DecimalNumber
    client_name: str
    expiry_date: date | None = None
    status: Literal["warning", "ok"]
    stock_unit: str = "ШТ"


class BalanceUploadError(BaseModel):
    row: int
    message: str


class BalanceUploadResult(BaseModel):
    uploaded: int
    created: int
    updated: int
    errors: int
    message: str
    error_details: list[BalanceUploadError]


class BalanceSyncUser(BaseModel):
    id: UUID
    username: str
    full_name: str
    role: str


class BalanceSyncInfo(BaseModel):
    last_balances_sync_at: datetime | None = None
    last_balances_sync_by: BalanceSyncUser | None = None


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


class ExecuteOneTimeRequest(BaseModel):
    order_number: str = Field(min_length=1, max_length=100)
    comment: str | None = None


class ExecuteOneTimeData(BaseModel):
    id: UUID
    status: str
    executed_at: datetime
    executed_by: UUID
    order_number: str
    executed_comment: str | None = None


class OneTimeItem(BaseModel):
    product_code: int
    product_name: str
    warehouse_code: int
    warehouse_name: str
    quantity: DecimalNumber
    unit: str


class OneTimeListItem(BaseModel):
    id: UUID
    client_name: str
    status: str
    initiator: UserBrief
    items: list[OneTimeItem]
    created_at: datetime
    order_number: str | None = None
    executed_at: datetime | None = None


class OneTimeInitiator(BaseModel):
    id: UUID
    username: str
    full_name: str
