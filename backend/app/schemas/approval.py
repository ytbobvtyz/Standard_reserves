from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import DecimalNumber
from app.schemas.user import UserBrief


class ApprovalItemChange(BaseModel):
    product_code: int
    warehouse_code: int
    quantity_approved: DecimalNumber = Field(gt=0)
    rejected: bool = False


class ApprovalActionRequest(BaseModel):
    action: Literal["approve", "reject"]
    items: list[ApprovalItemChange] | None = None
    comment: str | None = None
    expiry_date: date | None = Field(
        default=None,
        description="От 3 до 6 месяцев от даты создания запроса",
    )


class ApprovalItemCoverage(BaseModel):
    existing_nz: DecimalNumber | None = None
    monthly_sales: DecimalNumber | None = None
    warehouse_monthly_sales: DecimalNumber | None = None
    product_monthly_sales: DecimalNumber | None = None


class ApprovalRelatedProduct(BaseModel):
    """One related article and its own average sales, in the line unit."""

    code: int
    name: str
    avg_sales: DecimalNumber = Decimal("0")
    avg_sales_warehouse: DecimalNumber = Decimal("0")
    avg_sales_all_warehouses: DecimalNumber = Decimal("0")


class ApprovalPendingItem(BaseModel):
    product_code: int
    product_name: str
    warehouse_code: int
    warehouse_name: str
    quantity_requested: DecimalNumber
    quantity_approved: DecimalNumber | None = None
    rejected: bool = False
    unit: str
    category: str
    category_factor: DecimalNumber
    long_distance: bool = False
    distance_factor: DecimalNumber
    requirement: DecimalNumber
    coverage: ApprovalItemCoverage = Field(default_factory=ApprovalItemCoverage)
    avg_sales_client_total: DecimalNumber = Decimal("0")
    avg_sales_client_related: DecimalNumber = Decimal("0")
    avg_sales_product_warehouse_total: DecimalNumber = Decimal("0")
    avg_sales_product_warehouse_related: DecimalNumber = Decimal("0")
    avg_sales_product_all_warehouses_total: DecimalNumber = Decimal("0")
    avg_sales_product_all_warehouses_related: DecimalNumber = Decimal("0")
    related_products: list[ApprovalRelatedProduct] = Field(default_factory=list)


class ApprovalPendingRequest(BaseModel):
    id: UUID
    request_type: str
    client_id: UUID
    client_name: str
    auto_complete_previous: bool = False
    initiator: UserBrief
    items: list[ApprovalPendingItem]
    expiry_date: date | None = None
    created_at: datetime


class ApprovalActorBrief(BaseModel):
    id: UUID
    full_name: str


class ApprovalActionResult(BaseModel):
    id: UUID
    status: str
    pp_approved_at: datetime | None = None
    pp_approved_by: ApprovalActorBrief | None = None
    pp_action: str | None = None
    comment_pp: str | None = None
    economy_approved_at: datetime | None = None
    economy_approved_by: ApprovalActorBrief | None = None
    economy_action: str | None = None
    comment_economy: str | None = None
