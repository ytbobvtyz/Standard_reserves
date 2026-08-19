from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import APIError
from app.models.normative import Normative
from app.models.request import Request
from app.models.request_item import RequestItem
from app.models.request_item_history import RequestItemHistory
from app.models.user import User
from app.schemas.approval import (
    ApprovalActionRequest,
    ApprovalActionResult,
    ApprovalActorBrief,
    ApprovalPendingItem,
    ApprovalPendingRequest,
)
from app.schemas.user import UserBrief
from app.services.requests import load_request

Stage = Literal["pp", "economy"]

PP_STATUS = "pp_approved"
ECONOMY_STATUS = "economy_check"


def _normalize_comment(comment: str | None) -> str | None:
    if comment is None:
        return None
    stripped = comment.strip()
    return stripped or None


def _actor_brief(user: User | None) -> ApprovalActorBrief | None:
    if user is None:
        return None
    return ApprovalActorBrief(id=user.id, full_name=user.full_name)


def to_pending(request: Request) -> ApprovalPendingRequest:
    return ApprovalPendingRequest(
        id=request.id,
        request_type=request.request_type,
        client_name=request.client_name,
        initiator=UserBrief.model_validate(request.initiator),
        items=[
            ApprovalPendingItem(
                product_code=item.product_code,
                product_name=item.product.name,
                warehouse_code=item.warehouse_code,
                warehouse_name=item.warehouse.name,
                quantity_requested=item.quantity_requested,
                quantity_approved=item.quantity_approved,
                unit=item.unit,
            )
            for item in request.items
        ],
        created_at=request.created_at,
    )


def to_action_result(request: Request) -> ApprovalActionResult:
    return ApprovalActionResult(
        id=request.id,
        status=request.status,
        pp_approved_at=request.pp_approved_at,
        pp_approved_by=_actor_brief(request.pp_approver),
        pp_action=request.pp_action,
        comment_pp=request.comment_pp,
        economy_approved_at=request.economy_approved_at,
        economy_approved_by=_actor_brief(request.economy_approver),
        economy_action=request.economy_action,
        comment_economy=request.comment_economy,
    )


PENDING_OPTIONS = (
    selectinload(Request.items).selectinload(RequestItem.product),
    selectinload(Request.items).selectinload(RequestItem.warehouse),
    selectinload(Request.initiator),
)


async def list_pending(
    db: AsyncSession,
    *,
    status: str,
    request_type: str | None,
    page: int,
    limit: int,
) -> tuple[list[Request], int]:
    conditions = [Request.deleted_at.is_(None), Request.status == status]
    if request_type:
        conditions.append(Request.request_type == request_type)

    total = await db.scalar(
        select(func.count()).select_from(Request).where(*conditions)
    )
    result = await db.execute(
        select(Request)
        .options(*PENDING_OPTIONS)
        .where(*conditions)
        .order_by(Request.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    return list(result.scalars().unique().all()), total or 0


def _item_key(item: RequestItem) -> tuple[int, int]:
    return (item.product_code, item.warehouse_code)


async def _apply_edits(
    db: AsyncSession,
    request: Request,
    body: ApprovalActionRequest,
    user: User,
    comment: str | None,
) -> None:
    if not body.items:
        raise APIError(
            400,
            "VALIDATION_ERROR",
            "Для действия edit укажите позиции с новым объемом",
        )

    items_by_key = {_item_key(item): item for item in request.items}
    for change in body.items:
        if change.quantity_approved <= 0:
            raise APIError(
                400,
                "VALIDATION_ERROR",
                "Утвержденное количество должно быть больше 0",
            )
        item = items_by_key.get((change.product_code, change.warehouse_code))
        if item is None:
            raise APIError(
                400,
                "ITEM_NOT_FOUND",
                f"Позиция {change.product_code}/{change.warehouse_code} не найдена",
            )
        old_value = item.quantity_approved
        item.quantity_approved = Decimal(change.quantity_approved)
        db.add(
            RequestItemHistory(
                request_item_id=item.id,
                field_name="quantity_approved",
                old_value=old_value,
                new_value=item.quantity_approved,
                changed_by=user.id,
                comment=comment,
            )
        )


async def _ensure_normatives(db: AsyncSession, request: Request) -> None:
    if request.request_type != "normative":
        return
    if request.expiry_date is None:
        raise APIError(
            400,
            "VALIDATION_ERROR",
            "Для нормативного запроса отсутствует срок действия",
        )

    existing = await db.scalar(
        select(func.count())
        .select_from(Normative)
        .where(Normative.request_id == request.id, Normative.deleted_at.is_(None))
    )
    if existing:
        return

    for item in request.items:
        category = item.product.category.strip()
        db.add(
            Normative(
                request_id=request.id,
                product_code=item.product_code,
                warehouse_code=item.warehouse_code,
                quantity=item.quantity_approved or item.quantity_requested,
                unit=item.unit,
                client_name=request.client_name,
                expiry_date=request.expiry_date,
                category=category,
            )
        )


def _next_status(stage: Stage, action: str, request: Request) -> str:
    if action == "reject":
        return "rejected"
    if stage == "pp":
        return "economy_check"
    if action == "edit":
        return "economy_rework"
    if request.request_type == "normative":
        return "active"
    return "approved"


async def apply_action(
    db: AsyncSession,
    *,
    request_id: UUID,
    user: User,
    body: ApprovalActionRequest,
    stage: Stage,
) -> ApprovalActionResult:
    expected_status = PP_STATUS if stage == "pp" else ECONOMY_STATUS
    request = await load_request(db, request_id)
    if request.status != expected_status:
        raise APIError(
            400,
            "INVALID_STATUS",
            "Действие недоступно для текущего статуса запроса",
        )

    comment = _normalize_comment(body.comment)
    if body.action == "reject" and comment is None:
        raise APIError(
            400,
            "VALIDATION_ERROR",
            "Комментарий обязателен при отказе",
        )

    now = datetime.now(UTC)
    try:
        if body.action == "edit":
            await _apply_edits(db, request, body, user, comment)

        request.status = _next_status(stage, body.action, request)
        if stage == "pp":
            request.pp_action = body.action
            request.pp_approved_at = now
            request.pp_approver = user
            request.comment_pp = comment
        else:
            request.economy_action = body.action
            request.economy_approved_at = now
            request.economy_approver = user
            request.comment_economy = comment
            if body.action == "approve":
                request.approved_at = now
                await db.flush()
                await _ensure_normatives(db, request)

        await db.commit()
    except APIError:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        raise

    result = to_action_result(request)
    actor = ApprovalActorBrief(id=user.id, full_name=user.full_name)
    if stage == "pp":
        result.pp_approved_by = actor
    else:
        result.economy_approved_by = actor
    return result
