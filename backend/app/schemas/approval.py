from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import DecimalNumber
from app.schemas.user import UserBrief


class ApprovalItemChange(BaseModel):
    product_code: int
    warehouse_code: int
    quantity_approved: DecimalNumber = Field(gt=0)


class ApprovalActionRequest(BaseModel):
    action: Literal["approve", "reject"]
    items: list[ApprovalItemChange] | None = None
    comment: str | None = None
    expiry_date: date | None = Field(
        default=None,
        description="Не позже 6 месяцев от даты создания запроса",
    )


class ApprovalPendingItem(BaseModel):
    product_code: int
    product_name: str
    warehouse_code: int
    warehouse_name: str
    quantity_requested: DecimalNumber
    quantity_approved: DecimalNumber | None = None
    unit: str


class ApprovalPendingRequest(BaseModel):
    id: UUID
    request_type: str
    client_name: str
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
