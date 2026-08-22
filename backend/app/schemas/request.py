from datetime import UTC, date, datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.exceptions import APIError
from app.models.request import Request as RequestModel
from app.schemas.common import DecimalNumber
from app.schemas.user import UserBrief

INVALID_EXPIRY_DATE_CODE = "INVALID_EXPIRY_DATE"
INVALID_EXPIRY_DATE_MESSAGE = (
    "Срок не может превышать 6 месяцев от даты создания"
)
EXPIRY_DATE_TOO_LATE_CODE = "BAD_REQUEST"
EXPIRY_DATE_TOO_LATE_MESSAGE = "Дата окончания не может быть позже текущей"
EXPIRY_DATE_IN_PAST_CODE = "BAD_REQUEST"
EXPIRY_DATE_IN_PAST_MESSAGE = (
    "Дата окончания не может быть раньше сегодняшнего дня"
)
CANNOT_DELETE_APPROVED_CODE = "BAD_REQUEST"
CANNOT_DELETE_APPROVED_MESSAGE = (
    "Невозможно удалить запрос после финального согласования"
)
ALLOWED_DELETE_STATUSES = frozenset(
    {"draft", "pp_approved", "economy_check", "rejected", "expired"}
)


def validate_expiry_date_limit(
    expiry_date: date | None,
    created_at: datetime | None = None,
) -> None:
    if expiry_date is None:
        return
    reference = created_at or datetime.now(UTC)
    if not RequestModel.validate_expiry_date(expiry_date, reference):
        raise APIError(400, INVALID_EXPIRY_DATE_CODE, INVALID_EXPIRY_DATE_MESSAGE)


def validate_expiry_date_decrease(
    new_expiry: date,
    current_expiry: date | None,
    *,
    today: date | None = None,
) -> None:
    reference_today = today or datetime.now(UTC).date()
    if new_expiry < reference_today:
        raise APIError(400, EXPIRY_DATE_IN_PAST_CODE, EXPIRY_DATE_IN_PAST_MESSAGE)
    if current_expiry is not None and new_expiry > current_expiry:
        raise APIError(400, EXPIRY_DATE_TOO_LATE_CODE, EXPIRY_DATE_TOO_LATE_MESSAGE)


class RequestItemCreate(BaseModel):
    product_code: int
    warehouse_code: int
    quantity_requested: DecimalNumber = Field(gt=0)
    unit: Literal["шт", "т"]
    comment: str | None = None


class RequestCreate(BaseModel):
    request_type: Literal["normative", "one_time"]
    client_name: str = Field(min_length=1, max_length=500)
    expiry_date: date | None = Field(
        default=None,
        description="Не позже 6 месяцев от даты создания",
    )
    items: list[RequestItemCreate] = Field(min_length=1)
    comment: str | None = None

    @model_validator(mode="after")
    def expiry_within_six_months(self) -> Self:
        if self.expiry_date is None:
            return self
        # 400 INVALID_EXPIRY_DATE выбрасывается в сервисе, а не через 422 Pydantic.
        if not RequestModel.validate_expiry_date(
            self.expiry_date, datetime.now(UTC)
        ):
            return self
        return self


class RequestUpdate(BaseModel):
    client_name: str | None = Field(default=None, min_length=1, max_length=500)
    expiry_date: date | None = Field(
        default=None,
        description="Не позже 6 месяцев от даты создания запроса",
    )
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
    order_number: str | None = None
    executed_at: datetime | None = None
    executed_comment: str | None = None
    executed_by: UserBrief | None = None
    items: list[RequestItemDetail]
    approvals: RequestApprovals
    history: list[RequestHistoryEntry]
    created_at: datetime
    updated_at: datetime


class RequestStatusData(BaseModel):
    id: UUID
    status: str
    updated_at: datetime


class RequestExpiryUpdate(BaseModel):
    expiry_date: date


class RequestExpiryData(BaseModel):
    id: UUID
    status: str
    expiry_date: date | None = None
    updated_at: datetime
