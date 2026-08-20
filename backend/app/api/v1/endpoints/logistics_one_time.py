from datetime import date
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_roles
from app.models.user import User
from app.schemas.common import PaginatedResponse, PaginationMeta, SuccessResponse
from app.schemas.logistics import (
    ExecuteOneTimeData,
    ExecuteOneTimeRequest,
    OneTimeInitiator,
    OneTimeListItem,
)
from app.services import logistics_one_time as service

router = APIRouter(prefix="/logistics/one-time", tags=["Логистика — разовые"])

OneTimeStatus = Literal["approved", "executed", "rejected"]


@router.get("/list", response_model=PaginatedResponse[list[OneTimeListItem]])
async def list_one_time_requests(
    warehouse_code: int | None = Query(default=None),
    client_name: str | None = Query(default=None),
    initiator_id: UUID | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    status: OneTimeStatus | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    _current_user: User = Depends(require_roles("logistics")),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[list[OneTimeListItem]]:
    items, total = await service.list_one_time_requests(
        db,
        warehouse_code=warehouse_code,
        client_name=client_name,
        initiator_id=initiator_id,
        from_date=from_date,
        to_date=to_date,
        status=status,
        page=page,
        limit=limit,
    )
    return PaginatedResponse(
        data=items,
        meta=PaginationMeta(page=page, limit=limit, total=total),
    )


@router.get("/initiators", response_model=SuccessResponse[list[OneTimeInitiator]])
async def list_initiators(
    _current_user: User = Depends(require_roles("logistics")),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[list[OneTimeInitiator]]:
    return SuccessResponse(data=await service.list_initiators(db))


@router.get("/clients", response_model=SuccessResponse[list[str]])
async def list_clients(
    _current_user: User = Depends(require_roles("logistics")),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[list[str]]:
    return SuccessResponse(data=await service.list_clients(db))


@router.get("/{request_id}/export")
async def export_one_time(
    request_id: UUID,
    _current_user: User = Depends(require_roles("logistics")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    content = await service.export_one_time_excel(db, request_id)
    return Response(
        content=content,
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": (
                f'attachment; filename="one-time-{request_id}.xlsx"'
            )
        },
    )


@router.post(
    "/{request_id}/execute",
    response_model=SuccessResponse[ExecuteOneTimeData],
)
async def execute_one_time(
    request_id: UUID,
    body: ExecuteOneTimeRequest,
    current_user: User = Depends(require_roles("logistics")),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[ExecuteOneTimeData]:
    data = await service.execute_one_time(db, request_id, body, current_user)
    return SuccessResponse(data=data)
