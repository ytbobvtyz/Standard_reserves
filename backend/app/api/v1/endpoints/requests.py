from datetime import date
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Select, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db
from app.models.request import Request
from app.models.request_item import RequestItem
from app.models.user import User
from app.schemas.common import (
    MessageResponse,
    PaginatedResponse,
    PaginationMeta,
    SuccessResponse,
)
from app.schemas.request import (
    RequestCreate,
    RequestCreated,
    RequestDetail,
    RequestListItem,
    RequestStatusData,
    RequestUpdate,
)
from app.services.requests import (
    apply_own_requests_scope,
    create_request,
    delete_draft,
    ensure_draft_owner,
    get_visible_request,
    load_request,
    submit_draft,
    to_detail,
    to_list_item,
    update_draft,
)

router = APIRouter(tags=["Запросы"])


def _paginate(stmt: Select, page: int, limit: int) -> Select:
    return stmt.offset((page - 1) * limit).limit(limit)


@router.post(
    "/requests",
    response_model=SuccessResponse[RequestCreated],
    status_code=201,
)
async def create_request_endpoint(
    body: RequestCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[RequestCreated]:
    data = await create_request(db, current_user, body)
    return SuccessResponse(data=data)


@router.get("/requests", response_model=PaginatedResponse[list[RequestListItem]])
async def list_requests(
    type: Literal["normative", "one_time"] | None = Query(default=None),
    status: str | None = Query(default=None),
    client_name: str | None = Query(default=None),
    initiator_id: UUID | None = Query(default=None),
    warehouse_code: int | None = Query(default=None),
    product_code: int | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[list[RequestListItem]]:
    conditions = [Request.deleted_at.is_(None)]
    scoped_initiator = apply_own_requests_scope(current_user)
    if scoped_initiator is not None:
        conditions.append(Request.initiator_id == scoped_initiator)
    elif initiator_id is not None:
        conditions.append(Request.initiator_id == initiator_id)
    if type:
        conditions.append(Request.request_type == type)
    if status:
        conditions.append(Request.status == status)
    if client_name:
        conditions.append(Request.client_name.ilike(f"%{client_name.strip()}%"))
    if from_date:
        conditions.append(func.date(Request.created_at) >= from_date)
    if to_date:
        conditions.append(func.date(Request.created_at) <= to_date)
    if warehouse_code is not None:
        conditions.append(
            exists(
                select(RequestItem.id).where(
                    RequestItem.request_id == Request.id,
                    RequestItem.warehouse_code == warehouse_code,
                )
            )
        )
    if product_code is not None:
        conditions.append(
            exists(
                select(RequestItem.id).where(
                    RequestItem.request_id == Request.id,
                    RequestItem.product_code == product_code,
                )
            )
        )

    total = await db.scalar(
        select(func.count()).select_from(Request).where(*conditions)
    )
    result = await db.execute(
        _paginate(
            select(Request)
            .options(selectinload(Request.items), selectinload(Request.initiator))
            .where(*conditions)
            .order_by(Request.created_at.desc()),
            page,
            limit,
        )
    )
    requests = result.scalars().unique().all()
    return PaginatedResponse(
        data=[to_list_item(item) for item in requests],
        meta=PaginationMeta(page=page, limit=limit, total=total or 0),
    )


@router.get("/requests/{request_id}", response_model=SuccessResponse[RequestDetail])
async def get_request(
    request_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[RequestDetail]:
    request = await get_visible_request(db, request_id, current_user)
    return SuccessResponse(data=to_detail(request))


@router.put("/requests/{request_id}", response_model=SuccessResponse[RequestStatusData])
async def update_request(
    request_id: UUID,
    body: RequestUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[RequestStatusData]:
    request = await load_request(db, request_id)
    ensure_draft_owner(request, current_user)
    updated = await update_draft(db, request, body)
    return SuccessResponse(
        data=RequestStatusData(
            id=updated.id,
            status=updated.status,
            updated_at=updated.updated_at,
        )
    )


@router.delete("/requests/{request_id}", response_model=MessageResponse)
async def delete_request(
    request_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    request = await load_request(db, request_id)
    ensure_draft_owner(request, current_user)
    await delete_draft(db, request)
    return MessageResponse(message="Запрос удален")


@router.post(
    "/requests/{request_id}/submit",
    response_model=SuccessResponse[RequestStatusData],
)
async def submit_request(
    request_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[RequestStatusData]:
    request = await load_request(db, request_id)
    ensure_draft_owner(request, current_user)
    submitted = await submit_draft(db, request)
    return SuccessResponse(
        data=RequestStatusData(
            id=submitted.id,
            status=submitted.status,
            updated_at=submitted.updated_at,
        )
    )
