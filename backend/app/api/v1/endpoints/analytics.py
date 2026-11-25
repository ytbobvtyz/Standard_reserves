from datetime import UTC, date, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.exceptions import APIError
from app.models.user import User
from app.schemas.analytics import (
    AnalyticsFiltersData,
    ClientAnalyticsData,
    Granularity,
    StockDynamicsBounds,
    StockDynamicsData,
    StockSummaryData,
)
from app.schemas.common import SuccessResponse
from app.services import analytics as service
from app.services import client_analytics as client_service

router = APIRouter(prefix="/analytics", tags=["Аналитика"])


def _optional_uuid_list(values: list[str] | None) -> list[UUID] | None:
    """Нет параметра — None (все). Пустое значение — пустой список (никого)."""
    if values is None:
        return None
    parsed: list[UUID] = []
    for raw in values:
        text = raw.strip()
        if not text:
            continue
        try:
            parsed.append(UUID(text))
        except ValueError as exc:
            raise APIError(400, "VALIDATION_ERROR", "Некорректный client_ids") from exc
    return parsed


def _optional_int_list(
    values: list[str] | None,
    *,
    error: str = "Некорректный warehouse_codes",
) -> list[int] | None:
    if values is None:
        return None
    parsed: list[int] = []
    for raw in values:
        text = raw.strip()
        if not text:
            continue
        try:
            parsed.append(int(text))
        except ValueError as exc:
            raise APIError(400, "VALIDATION_ERROR", error) from exc
    return parsed


@router.get("/filters", response_model=SuccessResponse[AnalyticsFiltersData])
async def get_analytics_filters(
    product_code: int | None = Query(default=None),
    stock_product_codes: list[str] | None = Query(default=None),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[AnalyticsFiltersData]:
    data = await service.get_analytics_filters(
        db,
        product_code=product_code,
        stock_product_codes=_optional_int_list(
            stock_product_codes,
            error="Некорректный stock_product_codes",
        ),
        today=datetime.now(UTC).date(),
    )
    return SuccessResponse(data=data)


@router.get(
    "/stock-dynamics/bounds",
    response_model=SuccessResponse[StockDynamicsBounds],
)
async def get_stock_bounds(
    product_code: int = Query(),
    warehouse_code: int | None = Query(default=None),
    warehouse_codes: list[str] | None = Query(default=None),
    department_id: UUID | None = Query(default=None),
    client_id: UUID | None = Query(default=None),
    client_ids: list[str] | None = Query(default=None),
    stock_product_codes: list[str] | None = Query(default=None),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[StockDynamicsBounds]:
    data = await service.get_stock_bounds(
        db,
        product_code=product_code,
        warehouse_code=warehouse_code,
        warehouse_codes=_optional_int_list(warehouse_codes),
        department_id=department_id,
        client_id=client_id,
        client_ids=_optional_uuid_list(client_ids),
        stock_product_codes=_optional_int_list(
            stock_product_codes,
            error="Некорректный stock_product_codes",
        ),
    )
    return SuccessResponse(data=data)


@router.get("/stock-summary", response_model=SuccessResponse[StockSummaryData])
async def get_stock_summary(
    product_code: int = Query(),
    warehouse_code: int | None = Query(default=None),
    warehouse_codes: list[str] | None = Query(default=None),
    department_id: UUID | None = Query(default=None),
    client_id: UUID | None = Query(default=None),
    client_ids: list[str] | None = Query(default=None),
    stock_product_codes: list[str] | None = Query(default=None),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[StockSummaryData]:
    data = await service.get_stock_summary(
        db,
        product_code=product_code,
        warehouse_code=warehouse_code,
        warehouse_codes=_optional_int_list(warehouse_codes),
        department_id=department_id,
        client_id=client_id,
        client_ids=_optional_uuid_list(client_ids),
        stock_product_codes=_optional_int_list(
            stock_product_codes,
            error="Некорректный stock_product_codes",
        ),
        today=datetime.now(UTC).date(),
    )
    return SuccessResponse(data=data)


@router.get("/stock-dynamics", response_model=SuccessResponse[StockDynamicsData])
async def get_stock_dynamics(
    product_code: int = Query(),
    date_from: date = Query(),
    date_to: date = Query(),
    warehouse_code: int | None = Query(default=None),
    warehouse_codes: list[str] | None = Query(default=None),
    department_id: UUID | None = Query(default=None),
    client_id: UUID | None = Query(default=None),
    client_ids: list[str] | None = Query(default=None),
    stock_product_codes: list[str] | None = Query(default=None),
    granularity: Granularity = Query(default="month"),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[StockDynamicsData]:
    data = await service.get_stock_dynamics(
        db,
        product_code=product_code,
        warehouse_code=warehouse_code,
        warehouse_codes=_optional_int_list(warehouse_codes),
        department_id=department_id,
        client_id=client_id,
        client_ids=_optional_uuid_list(client_ids),
        stock_product_codes=_optional_int_list(
            stock_product_codes,
            error="Некорректный stock_product_codes",
        ),
        date_from=date_from,
        date_to=date_to,
        granularity=granularity,
    )
    return SuccessResponse(data=data)


@router.get(
    "/clients/{client_id}",
    response_model=SuccessResponse[ClientAnalyticsData],
)
async def get_client_analytics(
    client_id: UUID,
    date_from: date = Query(),
    date_to: date = Query(),
    warehouse_codes: list[str] | None = Query(default=None),
    product_codes: list[str] | None = Query(default=None),
    include_related: bool = Query(default=True),
    granularity: Granularity = Query(default="month"),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[ClientAnalyticsData]:
    data = await client_service.get_client_analytics(
        db,
        client_id=client_id,
        date_from=date_from,
        date_to=date_to,
        warehouse_codes=_optional_int_list(warehouse_codes),
        product_codes=_optional_int_list(
            product_codes,
            error="Некорректный product_codes",
        ),
        include_related=include_related,
        granularity=granularity,
        today=datetime.now(UTC).date(),
    )
    return SuccessResponse(data=data)
