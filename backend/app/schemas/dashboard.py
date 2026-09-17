from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import DecimalNumber, PaginationMeta

GroupBy = Literal["day", "week", "month"]
MassUnit = Literal["кг", "т"]
ExceptionStatus = Literal["critical", "attention"]


class DashboardNorthStar(BaseModel):
    active_count: int
    deficit_quantity: DecimalNumber
    coverage_pct: DecimalNumber
    expiring_30d: int
    avg_remaining_days: DecimalNumber | None = None
    unit: MassUnit = "т"


class TrendPoint(BaseModel):
    period: date
    total_normative: DecimalNumber
    count_active: int


class TrendSeries(BaseModel):
    key: str
    warehouse_code: int
    warehouse_name: str
    product_code: int | None = None
    product_name: str | None = None
    points: list[TrendPoint]


class NormativeTrendData(BaseModel):
    group_by: GroupBy
    date_from: date
    date_to: date
    unit: MassUnit = "т"
    periods: list[date]
    series: list[TrendSeries]


class DashboardExceptionItem(BaseModel):
    product_code: int
    product_name: str
    warehouse_code: int
    warehouse_name: str
    normative_quantity: DecimalNumber
    requirement: DecimalNumber
    available: DecimalNumber
    plan: DecimalNumber
    deficit: DecimalNumber
    unit: str
    status: ExceptionStatus
    request_id: UUID | None = None


class ExpiryCalendarDay(BaseModel):
    date: date
    count: int
    quantity: DecimalNumber


class ExpiryCalendarData(BaseModel):
    date_from: date
    date_to: date
    unit: MassUnit = "т"
    days: list[ExpiryCalendarDay]


class WarehouseCoverageItem(BaseModel):
    warehouse_code: int
    warehouse_name: str
    normative_quantity: DecimalNumber
    available: DecimalNumber
    planned: DecimalNumber
    deficit: DecimalNumber
    requirement: DecimalNumber
    coverage_pct: DecimalNumber
    mismatch: bool
    unit: MassUnit = "т"


class WarehouseCoverageData(BaseModel):
    unit: MassUnit = "т"
    warehouses: list[WarehouseCoverageItem]


class DashboardExceptionsResponse(BaseModel):
    status: str = Field(default="success")
    data: list[DashboardExceptionItem]
    meta: PaginationMeta
