from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import DecimalNumber


class ProductListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: int
    name: str
    category: str
    plant_id: int
    plant_name: str
    weight_kg: DecimalNumber
    monthly_consumption: DecimalNumber | None = None
    is_active: bool
    gtin: str | None = None
    mark_control: bool = False
    last_modified_at: datetime | None = None


class LastModifiedBy(BaseModel):
    id: UUID
    full_name: str


class ProductDetail(ProductListItem):
    description: str | None = None
    second_plant_id: int | None = None
    third_plant_id: int | None = None
    parent_code: int | None = None
    children_code: int | None = None
    last_modified_by: LastModifiedBy | None = None


class ProductUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=500)
    description: str | None = None
    category: str = Field(pattern="^[ABC]$")
    is_active: bool = True
    weight_kg: DecimalNumber = Field(gt=0)
    monthly_consumption: DecimalNumber | None = None
    gtin: str | None = None
    mark_control: bool = False
    plant_id: int
    second_plant_id: int | None = None
    third_plant_id: int | None = None
    parent_code: int | None = None
    children_code: int | None = None


class ProductUploadError(BaseModel):
    row: int
    message: str


class ProductUploadResult(BaseModel):
    created: int
    updated: int
    errors: int
    message: str
    error_details: list[ProductUploadError]


class RelatedProductItem(BaseModel):
    code: int
    name: str
    relation: str
    is_active: bool


class RelatedProductsData(BaseModel):
    product_code: int
    product_name: str
    related_products: list[RelatedProductItem]


class ObjectListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: int
    name: str
    city: str
    region: str | None = None
    address: str | None = None
    type: str
    is_active: bool


class UserReference(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: str
    full_name: str
    role: str
    department: str | None = None
    is_active: bool
