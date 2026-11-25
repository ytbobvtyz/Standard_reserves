from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import DecimalNumber

Granularity = Literal["day", "week", "month"]


class StockDynamicsData(BaseModel):
    dates: list[date]
    normative: list[DecimalNumber | None]
    available_min: list[DecimalNumber | None]
    available_median: list[DecimalNumber | None]
    available_max: list[DecimalNumber | None]
    full_stock_min: list[DecimalNumber | None]
    full_stock_median: list[DecimalNumber | None]
    full_stock_max: list[DecimalNumber | None]
    actual: list[DecimalNumber | None]
    unit: Literal["т"] = "т"


class StockDynamicsBounds(BaseModel):
    earliest_date: date | None = None


class StockMonthSummary(BaseModel):
    month: date
    available_median: DecimalNumber | None
    actual: DecimalNumber | None
    normative_avg: DecimalNumber | None


class StockSummaryData(BaseModel):
    months: list[StockMonthSummary]
    unit: Literal["т"] = "т"


class AnalyticsFilterClient(BaseModel):
    id: UUID
    name: str
    shipment_kg: DecimalNumber


class AnalyticsFilterWarehouse(BaseModel):
    code: int
    name: str
    shipment_kg: DecimalNumber


class AnalyticsFiltersData(BaseModel):
    clients: list[AnalyticsFilterClient]
    warehouses: list[AnalyticsFilterWarehouse]
    unit: Literal["кг"] = "кг"


class ClientAnalyticsChart(BaseModel):
    dates: list[date]
    normative: list[DecimalNumber | None]
    actual: list[DecimalNumber | None]
    unit: Literal["т"] = "т"


class ClientAnalyticsSlice(BaseModel):
    normative_tons: DecimalNumber
    avg_monthly_tons: DecimalNumber | None
    period_tons: DecimalNumber | None
    coverage_months: DecimalNumber | None
    outside_normative: bool


class ClientRelatedSales(BaseModel):
    code: int
    name: str
    avg_monthly_tons: DecimalNumber | None


class ClientWarehouseRow(BaseModel):
    code: int
    name: str
    normative_tons: DecimalNumber
    avg_monthly_tons: DecimalNumber | None
    period_tons: DecimalNumber | None
    coverage_months: DecimalNumber | None
    outside_normative: bool


class ClientProductRow(BaseModel):
    code: int
    name: str
    normative_tons: DecimalNumber
    avg_monthly_tons: DecimalNumber | None
    period_tons: DecimalNumber | None
    coverage_months: DecimalNumber | None
    outside_normative: bool
    related: list[ClientRelatedSales]


class ClientUnmatchedPoint(BaseModel):
    loading_point: str
    avg_monthly_tons: DecimalNumber | None
    period_tons: DecimalNumber | None
    coverage_months: DecimalNumber | None
    outside_normative: bool


class ClientAnalyticsData(BaseModel):
    client_id: UUID
    client_name: str
    department_name: str | None
    is_system: bool
    chart: ClientAnalyticsChart
    slice: ClientAnalyticsSlice
    warehouses: list[ClientWarehouseRow]
    products: list[ClientProductRow]
    unmatched: list[ClientUnmatchedPoint]
