from datetime import UTC, date, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.analytics import (
    Granularity,
    StockDynamicsBounds,
    StockDynamicsData,
    StockSummaryData,
)
from app.schemas.common import SuccessResponse
from app.services import analytics as service

router = APIRouter(prefix="/analytics", tags=["Аналитика"])


@router.get(
    "/stock-dynamics/bounds",
    response_model=SuccessResponse[StockDynamicsBounds],
)
async def get_stock_bounds(
    product_code: int = Query(),
    warehouse_code: int | None = Query(default=None),
    department_id: UUID | None = Query(default=None),
    client_id: UUID | None = Query(default=None),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[StockDynamicsBounds]:
    data = await service.get_stock_bounds(
        db,
        product_code=product_code,
        warehouse_code=warehouse_code,
        department_id=department_id,
        client_id=client_id,
    )
    return SuccessResponse(data=data)


@router.get("/stock-summary", response_model=SuccessResponse[StockSummaryData])
async def get_stock_summary(
    product_code: int = Query(),
    warehouse_code: int | None = Query(default=None),
    department_id: UUID | None = Query(default=None),
    client_id: UUID | None = Query(default=None),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[StockSummaryData]:
    data = await service.get_stock_summary(
        db,
        product_code=product_code,
        warehouse_code=warehouse_code,
        department_id=department_id,
        client_id=client_id,
        today=datetime.now(UTC).date(),
    )
    return SuccessResponse(data=data)


@router.get("/stock-dynamics", response_model=SuccessResponse[StockDynamicsData])
async def get_stock_dynamics(
    product_code: int = Query(),
    date_from: date = Query(),
    date_to: date = Query(),
    warehouse_code: int | None = Query(default=None),
    department_id: UUID | None = Query(default=None),
    client_id: UUID | None = Query(default=None),
    granularity: Granularity = Query(default="month"),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[StockDynamicsData]:
    data = await service.get_stock_dynamics(
        db,
        product_code=product_code,
        warehouse_code=warehouse_code,
        department_id=department_id,
        client_id=client_id,
        date_from=date_from,
        date_to=date_to,
        granularity=granularity,
    )
    return SuccessResponse(data=data)
