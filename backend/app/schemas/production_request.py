from datetime import date, datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import DecimalNumber
from app.schemas.user import UserBrief


class ProductionRequestItemData(BaseModel):
    id: UUID
    product_code: int
    warehouse_code: int
    quantity: DecimalNumber
    unit: str
    client_name: str
    category: str


class ProductionRequestListItem(BaseModel):
    id: UUID
    batch_id: UUID
    source: str
    uploaded_by: UserBrief
    client_name: str | None = None
    valid_from: date
    valid_to: date
    status: str
    items_count: int
    created_at: datetime


class ProductionRequestDetail(ProductionRequestListItem):
    items: list[ProductionRequestItemData]


class ProductionRequestUploadError(BaseModel):
    row: int
    message: str


class ProductionRequestUploadResult(BaseModel):
    production_request: ProductionRequestDetail | None = None
    total_rows: int
    imported_count: int
    error_count: int
    message: str
    error_details: list[ProductionRequestUploadError]


class ProductionRequestDatesUpdate(BaseModel):
    valid_from: date
    valid_to: date

    @model_validator(mode="after")
    def validate_range(self) -> Self:
        if self.valid_to < self.valid_from:
            raise ValueError("Дата окончания не может быть раньше даты начала")
        return self


class ProductionRequestUploadOptions(BaseModel):
    client_name: str | None = Field(default=None, max_length=500)
    valid_from: date
    valid_to: date

    @model_validator(mode="after")
    def validate_range(self) -> Self:
        if self.valid_to < self.valid_from:
            raise ValueError("Дата окончания не может быть раньше даты начала")
        return self
