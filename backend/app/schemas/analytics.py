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
