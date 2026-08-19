from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, Field, PlainSerializer

DecimalNumber = Annotated[
    Decimal,
    PlainSerializer(lambda value: float(value), return_type=float, when_used="json"),
]


class SuccessResponse[T](BaseModel):
    status: str = Field(default="success")
    data: T


class MessageResponse(BaseModel):
    status: str = Field(default="success")
    message: str


class PaginationMeta(BaseModel):
    page: int
    limit: int
    total: int


class PaginatedResponse[T](BaseModel):
    status: str = Field(default="success")
    data: T
    meta: PaginationMeta
