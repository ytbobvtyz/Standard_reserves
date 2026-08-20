from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse, SuccessResponse
from app.schemas.normative import (
    NormativeCalculateData,
    NormativeListItem,
    NormativeOnDateItem,
)
from app.services import normatives as service

router = APIRouter(tags=["Нормативы"])


@router.get("/normatives", response_model=PaginatedResponse[list[NormativeListItem]])
async def list_normatives(
    warehouse_code: int | None = Query(default=None),
    product_code: int | None = Query(default=None),
    client_name: str | None = Query(default=None),
    category: Literal["A", "B", "C"] | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[list[NormativeListItem]]:
    items, meta = await service.list_current_normatives(
        db,
        warehouse_code=warehouse_code,
        product_code=product_code,
        client_name=client_name,
        category=category,
        page=page,
        limit=limit,
    )
    return PaginatedResponse(data=items, meta=meta)


@router.get(
    "/normatives/on-date",
    response_model=SuccessResponse[list[NormativeOnDateItem]],
)
async def list_normatives_on_date(
    date: date = Query(...),
    warehouse_code: int | None = Query(default=None),
    product_code: int | None = Query(default=None),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[list[NormativeOnDateItem]]:
    items = await service.list_normatives_on_date(
        db,
        on_date=date,
        warehouse_code=warehouse_code,
        product_code=product_code,
    )
    return SuccessResponse(data=items)


@router.get(
    "/normatives/calculate",
    response_model=SuccessResponse[NormativeCalculateData],
)
async def calculate_normative(
    product_code: int = Query(...),
    warehouse_code: int = Query(...),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[NormativeCalculateData]:
    data = await service.calculate_normative(
        db,
        product_code=product_code,
        warehouse_code=warehouse_code,
    )
    return SuccessResponse(data=data)
