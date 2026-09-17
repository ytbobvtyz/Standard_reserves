from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.schemas.dashboard import (
    DashboardExceptionsResponse,
    DashboardNorthStar,
    ExpiryCalendarData,
    GroupBy,
    MassUnit,
    NormativeTrendData,
    WarehouseCoverageData,
)
from app.services import dashboard as service

router = APIRouter(prefix="/dashboard", tags=["Дашборд"])


@router.get("/summary", response_model=SuccessResponse[DashboardNorthStar])
async def get_summary(
    unit: MassUnit = Query(default="т"),
    warehouse_code: int | None = Query(default=None),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[DashboardNorthStar]:
    data = await service.get_summary(db, unit=unit, warehouse_code=warehouse_code)
    return SuccessResponse(data=data)


@router.get("/normative-trend", response_model=SuccessResponse[NormativeTrendData])
async def get_normative_trend(
    product_code: int | None = Query(default=None),
    warehouse_code: int | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    group_by: GroupBy = Query(default="week"),
    period: GroupBy | None = Query(
        default=None, description="Алиас group_by: day / week / month"
    ),
    unit: MassUnit = Query(default="т"),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[NormativeTrendData]:
    data = await service.get_normative_trend(
        db,
        product_code=product_code,
        warehouse_code=warehouse_code,
        date_from=date_from,
        date_to=date_to,
        group_by=period or group_by,
        unit=unit,
    )
    return SuccessResponse(data=data)


@router.get("/exceptions", response_model=DashboardExceptionsResponse)
async def list_exceptions(
    warehouse_code: int | None = Query(default=None),
    product_code: int | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=200),
    unit: MassUnit = Query(default="т"),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardExceptionsResponse:
    items, meta = await service.list_exceptions(
        db,
        warehouse_code=warehouse_code,
        product_code=product_code,
        page=page,
        limit=limit,
        unit=unit,
    )
    return DashboardExceptionsResponse(data=items, meta=meta)


@router.get(
    "/warehouse-coverage",
    response_model=SuccessResponse[WarehouseCoverageData],
)
async def get_warehouse_coverage(
    unit: MassUnit = Query(default="т"),
    warehouse_code: int | None = Query(default=None),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[WarehouseCoverageData]:
    data = await service.get_warehouse_coverage(
        db, unit=unit, warehouse_code=warehouse_code
    )
    return SuccessResponse(data=data)


@router.get("/expiry-calendar", response_model=SuccessResponse[ExpiryCalendarData])
async def get_expiry_calendar(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    unit: MassUnit = Query(default="т"),
    warehouse_code: int | None = Query(default=None),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[ExpiryCalendarData]:
    data = await service.get_expiry_calendar(
        db,
        date_from=date_from,
        date_to=date_to,
        unit=unit,
        warehouse_code=warehouse_code,
    )
    return SuccessResponse(data=data)
