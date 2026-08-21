from typing import Literal

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_roles
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.schemas.logistics import (
    BalanceUploadResult,
    DashboardResponse,
    GenerateOrdersBulkRequest,
    GenerateOrdersData,
    GenerateOrdersRequest,
)
from app.services import logistics_normative as service

router = APIRouter(prefix="/logistics/normative", tags=["Логистика — нормативы"])
LOGISTICS_ONLY = require_roles("logistics")

FilterMode = Literal["all", "with_normatives", "deficit_only"]
Unit = Literal["шт", "т"]


def _parse_product_codes(raw: str | None) -> list[int] | None:
    if raw is None or not raw.strip():
        return None
    codes: list[int] = []
    for part in raw.split(","):
        value = part.strip()
        if not value:
            continue
        codes.append(int(value))
    return codes or None


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    warehouse_code: int | None = Query(default=None),
    filter_mode: FilterMode = Query(default="with_normatives"),
    unit: Unit = Query(default="шт"),
    _current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardResponse:
    return await service.get_dashboard(
        db,
        warehouse_code=warehouse_code,
        filter_mode=filter_mode,
        unit=unit,
    )


@router.post("/upload", response_model=SuccessResponse[BalanceUploadResult])
async def upload_balances(
    file: UploadFile = File(...),
    _current_user: User = Depends(LOGISTICS_ONLY),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[BalanceUploadResult]:
    content = await file.read()
    data = await service.upload_balances(
        db,
        content,
        file.filename or "balances.xlsx",
    )
    return SuccessResponse(data=data)


@router.get("/export")
async def export_orders(
    warehouse_code: int | None = Query(default=None),
    product_codes: str | None = Query(default=None),
    unit: Unit = Query(default="шт"),
    _current_user: User = Depends(LOGISTICS_ONLY),
    db: AsyncSession = Depends(get_db),
) -> Response:
    content = await service.export_excel(
        db,
        warehouse_code=warehouse_code,
        product_codes=_parse_product_codes(product_codes),
        unit=unit,
    )
    return Response(
        content=content,
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers={"Content-Disposition": 'attachment; filename="orders.xlsx"'},
    )


@router.post(
    "/generate-orders",
    response_model=SuccessResponse[GenerateOrdersData],
)
async def generate_orders_bulk(
    body: GenerateOrdersBulkRequest,
    _current_user: User = Depends(LOGISTICS_ONLY),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[GenerateOrdersData]:
    data = await service.generate_orders_for_warehouses(
        db,
        warehouse_codes=body.warehouse_codes,
        product_codes=body.product_codes,
    )
    return SuccessResponse(data=data)


@router.post(
    "/{warehouse_code}/generate-orders",
    response_model=SuccessResponse[GenerateOrdersData],
)
async def generate_orders(
    warehouse_code: int,
    body: GenerateOrdersRequest | None = None,
    _current_user: User = Depends(LOGISTICS_ONLY),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[GenerateOrdersData]:
    data = await service.generate_orders(
        db,
        warehouse_code=warehouse_code,
        product_codes=body.product_codes if body else None,
    )
    return SuccessResponse(data=data)
