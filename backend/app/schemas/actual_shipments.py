from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import DecimalNumber

ShipmentUnit = Literal["шт", "кг", "т"]


class ActualShipmentError(BaseModel):
    row: int
    message: str


class ActualShipmentPreviewRow(BaseModel):
    row: int
    client_id: UUID
    client_code: int
    client_name: str
    product_code: int
    product_name: str
    quantity: DecimalNumber
    unit: ShipmentUnit
    shipment_date: date
    invoice_number: str | None = None
    route: str | None = None


class ActualShipmentUploadResult(BaseModel):
    saved: bool
    total_rows: int
    valid_rows: int
    inserted: int
    errors: int
    message: str
    preview: list[ActualShipmentPreviewRow]
    error_details: list[ActualShipmentError]


class ActualShipmentListItem(BaseModel):
    id: UUID
    client_id: UUID
    client_code: int
    client_name: str
    product_code: int
    product_name: str
    quantity: DecimalNumber
    unit: ShipmentUnit
    shipment_date: date
    invoice_number: str | None = None
    route: str | None = None
