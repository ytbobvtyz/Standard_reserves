from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_roles
from app.models.user import User
from app.schemas.approval import (
    ApprovalActionRequest,
    ApprovalActionResult,
    ApprovalPendingRequest,
)
from app.schemas.common import PaginatedResponse, PaginationMeta, SuccessResponse
from app.services.approvals import apply_action, list_pending, to_pending

router = APIRouter(prefix="/approvals", tags=["Согласование"])


async def _pending_response(
    db: AsyncSession,
    *,
    status: str,
    request_type: str | None,
    page: int,
    limit: int,
) -> PaginatedResponse[list[ApprovalPendingRequest]]:
    requests, total = await list_pending(
        db,
        status=status,
        request_type=request_type,
        page=page,
        limit=limit,
    )
    return PaginatedResponse(
        data=[to_pending(item) for item in requests],
        meta=PaginationMeta(page=page, limit=limit, total=total),
    )


@router.get(
    "/pp/pending",
    response_model=PaginatedResponse[list[ApprovalPendingRequest]],
)
async def list_pp_pending(
    type: Literal["normative", "one_time"] | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    _current_user: User = Depends(require_roles("pp")),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[list[ApprovalPendingRequest]]:
    return await _pending_response(
        db,
        status="pp_approved",
        request_type=type,
        page=page,
        limit=limit,
    )


@router.post(
    "/pp/{request_id}/action",
    response_model=SuccessResponse[ApprovalActionResult],
)
async def pp_action(
    request_id: UUID,
    body: ApprovalActionRequest,
    current_user: User = Depends(require_roles("pp")),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[ApprovalActionResult]:
    data = await apply_action(
        db,
        request_id=request_id,
        user=current_user,
        body=body,
        stage="pp",
    )
    return SuccessResponse(data=data)


@router.get(
    "/economy/pending",
    response_model=PaginatedResponse[list[ApprovalPendingRequest]],
)
async def list_economy_pending(
    type: Literal["normative", "one_time"] | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    _current_user: User = Depends(require_roles("economist")),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[list[ApprovalPendingRequest]]:
    return await _pending_response(
        db,
        status="economy_check",
        request_type=type,
        page=page,
        limit=limit,
    )


@router.post(
    "/economy/{request_id}/action",
    response_model=SuccessResponse[ApprovalActionResult],
)
async def economy_action(
    request_id: UUID,
    body: ApprovalActionRequest,
    current_user: User = Depends(require_roles("economist")),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[ApprovalActionResult]:
    data = await apply_action(
        db,
        request_id=request_id,
        user=current_user,
        body=body,
        stage="economy",
    )
    return SuccessResponse(data=data)
