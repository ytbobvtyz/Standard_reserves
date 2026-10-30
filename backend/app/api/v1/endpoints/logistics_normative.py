import zipfile
from datetime import date, datetime
from io import BytesIO
from typing import Literal

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_roles
from app.models.user import User
from app.schemas.common import PaginatedResponse, PaginationMeta, SuccessResponse
from app.schemas.logistics import (
    B2BExportRequest,
    BalanceHistoryItem,
    BalancePreviewResult,
    BalanceSyncInfo,
    BalanceUploadResult,
    DashboardResponse,
    GenerateOrdersBulkRequest,
    GenerateOrdersData,
    GenerateOrdersRequest,
)
from app.services import b2b_export, balance_excel
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


@router.post("/preview", response_model=SuccessResponse[BalancePreviewResult])
async def preview_balances(
    available_file: UploadFile = File(...),
    moving_file: UploadFile = File(...),
    _current_user: User = Depends(LOGISTICS_ONLY),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[BalancePreviewResult]:
    available_content = await available_file.read()
    moving_content = await moving_file.read()
    data = await balance_excel.preview_balances(
        db,
        available_content,
        available_file.filename or "available.xlsx",
        moving_content,
        moving_file.filename or "moving.xlsx",
    )
    return SuccessResponse(data=data)


@router.post("/upload", response_model=SuccessResponse[BalanceUploadResult])
async def upload_balances(
    available_file: UploadFile = File(...),
    moving_file: UploadFile = File(...),
    current_user: User = Depends(LOGISTICS_ONLY),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[BalanceUploadResult]:
    available_content = await available_file.read()
    moving_content = await moving_file.read()
    data = await balance_excel.upload_balances(
        db,
        available_content,
        available_file.filename or "available.xlsx",
        moving_content,
        moving_file.filename or "moving.xlsx",
        user_id=current_user.id,
    )
    return SuccessResponse(data=data)


@router.get("/history", response_model=PaginatedResponse[list[BalanceHistoryItem]])
async def list_balance_history(
    product_code: int | None = Query(default=None),
    warehouse_code: int | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    _current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[list[BalanceHistoryItem]]:
    items, total = await service.list_balance_history(
        db,
        product_code=product_code,
        warehouse_code=warehouse_code,
        date_from=date_from,
        date_to=date_to,
        page=page,
        limit=limit,
    )
    return PaginatedResponse(
        data=items,
        meta=PaginationMeta(page=page, limit=limit, total=total),
    )


@router.get("/history/dates", response_model=SuccessResponse[list[date]])
async def list_balance_snapshot_dates(
    _current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[list[date]]:
    dates = await service.list_balance_snapshot_dates(db)
    return SuccessResponse(data=dates)


@router.get("/sync-info", response_model=SuccessResponse[BalanceSyncInfo])
async def get_sync_info(
    _current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[BalanceSyncInfo]:
    data = await service.get_sync_info(db)
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


@router.post("/export-b2b")
async def export_b2b(
    body: B2BExportRequest,
    _current_user: User = Depends(LOGISTICS_ONLY),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Экспорт разнарядок B2B: ZIP с Excel-файлами по маршрутам."""
    exports = await b2b_export.generate_b2b_exports(db, body.routes)
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for filename, content in exports.items():
            archive.writestr(filename, content)
    stamp = datetime.now().strftime("%Y%m%d")
    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="b2b_orders_{stamp}.zip"'
        },
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
