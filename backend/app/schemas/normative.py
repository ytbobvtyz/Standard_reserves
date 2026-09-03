from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.common import DecimalNumber


class NormativeListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    request_id: UUID | None = None
    author_name: str | None = None
    product_code: int
    product_name: str
    category: str
    warehouse_code: int
    warehouse_name: str
    quantity: DecimalNumber
    unit: str
    client_name: str
    department_id: UUID | None = None
    department_name: str | None = None
    expiry_date: date
    created_at: datetime


class NormativeOnDateDetail(BaseModel):
    client_name: str
    quantity: DecimalNumber
    expiry_date: date
    department_id: UUID | None = None
    department_name: str | None = None
    request_id: UUID | None = None
    author_name: str | None = None


class NormativeOnDateItem(BaseModel):
    product_code: int
    product_name: str
    warehouse_code: int
    warehouse_name: str
    total_quantity: DecimalNumber
    unit: str
    category: str
    details: list[NormativeOnDateDetail]


class NormativeCalculateData(BaseModel):
    product_code: int
    product_name: str
    category: str
    warehouse_code: int
    warehouse_name: str
    monthly_consumption: DecimalNumber | None = None
    distance_factor: DecimalNumber
    category_factor: DecimalNumber
    calculated_normative: DecimalNumber | None = None
    unit: str
