from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import DecimalNumber
from app.schemas.user import UserBrief


class RequestItemCreate(BaseModel):
    product_code: int
    warehouse_code: int
    quantity_requested: DecimalNumber = Field(gt=0)
    unit: Literal["шт", "т"]
    comment: str | None = None


class RequestCreate(BaseModel):
    request_type: Literal["normative", "one_time"]
    client_name: str = Field(min_length=1, max_length=500)
    expiry_date: date | None = None
    items: list[RequestItemCreate] = Field(min_length=1)
    comment: str | None = None


class RequestUpdate(BaseModel):
    client_name: str | None = Field(default=None, min_length=1, max_length=500)
    expiry_date: date | None = None
    items: list[RequestItemCreate] | None = Field(default=None, min_length=1)
    comment: str | None = None


class RequestItemCreated(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_code: int
    warehouse_code: int
    quantity_requested: DecimalNumber
    quantity_approved: DecimalNumber | None = None
    unit: str
    comment: str | None = None


class RequestCreated(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    request_type: str
    status: str
    client_name: str
    initiator_id: UUID
    expiry_date: date | None = None
    items: list[RequestItemCreated]
    created_at: datetime


class RequestListItem(BaseModel):
    id: UUID
    request_type: str
    status: str
    client_name: str
    initiator: UserBrief
    items_count: int
    total_quantity: DecimalNumber
    expiry_date: date | None = None
    created_at: datetime


class ProductBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: int
    name: str
    category: str
    weight_kg: DecimalNumber


class WarehouseBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: int
    name: str


class RequestItemDetail(BaseModel):
    id: UUID
    product: ProductBrief
    warehouse: WarehouseBrief
    quantity_requested: DecimalNumber
    quantity_approved: DecimalNumber | None = None
    unit: str
    comment: str | None = None


class ApprovalActor(BaseModel):
    approved_at: datetime | None = None
    approved_by: UserBrief | None = None
    action: str | None = None


class RequestApprovals(BaseModel):
    pp: ApprovalActor
    economy: ApprovalActor


class RequestHistoryEntry(BaseModel):
    timestamp: datetime
    action: str
    user_name: str | None = None
    comment: str | None = None


class HistoryChangedBy(BaseModel):
    id: UUID
    full_name: str


class RequestItemHistoryEntry(BaseModel):
    item_id: UUID
    field_name: str
    old_value: DecimalNumber | None = None
    new_value: DecimalNumber | None = None
    changed_by: HistoryChangedBy
    changed_at: datetime
    comment: str | None = None


class RequestDetail(BaseModel):
    id: UUID
    request_type: str
    status: str
    client_name: str
    initiator: UserBrief
    initiator_comment: str | None = None
    comment_pp: str | None = None
    comment_economy: str | None = None
    expiry_date: date | None = None
    items: list[RequestItemDetail]
    approvals: RequestApprovals
    history: list[RequestHistoryEntry]
    created_at: datetime
    updated_at: datetime


class RequestStatusData(BaseModel):
    id: UUID
    status: str
    updated_at: datetime
