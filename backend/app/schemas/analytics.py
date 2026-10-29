from datetime import date
from typing import Literal

from pydantic import BaseModel

from app.schemas.common import DecimalNumber

Granularity = Literal["day", "week", "month"]


class StockDynamicsData(BaseModel):
    dates: list[date]
    normative: list[DecimalNumber | None]
    available_min: list[DecimalNumber | None]
    available_median: list[DecimalNumber | None]
    available_max: list[DecimalNumber | None]
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
