from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import DecimalNumber

ShipmentUnit = Literal["шт", "кг", "т"]


class ActualShipmentError(BaseModel):
    row: int
    message: str


class ActualShipmentMissingClient(BaseModel):
    client_code: int
    client_name: str | None = None
    rows: int


class ActualShipmentMissingProduct(BaseModel):
    product_code: int
    product_name: str | None = None
    rows: int


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
    loading_point: str
    invoice_number: str | None = None
    route: str | None = None


class ActualShipmentUploadResult(BaseModel):
    saved: bool
    total_rows: int
    valid_rows: int
    inserted: int
    skipped_rows: int
    errors: int
    message: str
    preview: list[ActualShipmentPreviewRow]
    error_details: list[ActualShipmentError]
    missing_clients: list[ActualShipmentMissingClient]
    missing_products: list[ActualShipmentMissingProduct]


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
    loading_point: str
    invoice_number: str | None = None
    route: str | None = None
