from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import APIError
from app.core.pagination import paginate
from app.models.client import SYSTEM_CLIENT_ID
from app.models.event import Event
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
from app.schemas.request import (
    validate_expiry_date_decrease,
    validate_expiry_date_limit,
)
from app.schemas.user import UserBrief
from app.services.clients import names_match
from app.services.coefficients import CoefficientSet, item_coefficient_fields
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


def to_pending(
    request: Request, coeffs: CoefficientSet | None = None
) -> ApprovalPendingRequest:
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
                category=fields["category"],
                category_factor=fields["category_factor"],
                long_distance=fields["long_distance"],
                distance_factor=fields["distance_factor"],
                requirement=fields["requirement"],
            )
            for item in request.items
            for fields in [
                item_coefficient_fields(
                    item.product,
                    item.warehouse,
                    (
                        item.quantity_approved
                        if item.quantity_approved is not None
                        else item.quantity_requested
                    ),
                    coeffs,
                )
            ]
        ],
        expiry_date=request.expiry_date,
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
    client_name: str | None = None,
) -> tuple[list[Request], int]:
    conditions = [Request.deleted_at.is_(None), Request.status == status]
    if request_type:
        conditions.append(Request.request_type == request_type)
    if client_name and client_name.strip():
        conditions.append(Request.client_name.ilike(f"%{client_name.strip()}%"))

    total = await db.scalar(
        select(func.count()).select_from(Request).where(*conditions)
    )
    result = await db.execute(
        paginate(
            select(Request)
            .options(*PENDING_OPTIONS)
            .where(*conditions)
            .order_by(Request.created_at.desc()),
            page,
            limit,
        )
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
            "Укажите позиции с новым объемом",
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
        old_value = await _approved_quantity_old_value(db, item)
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
        await db.flush()


async def _approved_quantity_old_value(
    db: AsyncSession,
    item: RequestItem,
) -> Decimal:
    has_history = await db.scalar(
        select(RequestItemHistory.id)
        .where(RequestItemHistory.request_item_id == item.id)
        .limit(1)
    )
    if has_history is None:
        return item.quantity_requested
    if item.quantity_approved is not None:
        return item.quantity_approved
    return item.quantity_requested


def _apply_expiry_update(
    request: Request,
    expiry_date: date | None,
    comment: str | None,
    *,
    restrict_decrease: bool = False,
) -> str | None:
    if expiry_date is None:
        return comment
    if restrict_decrease:
        validate_expiry_date_decrease(expiry_date, request.expiry_date)
    validate_expiry_date_limit(expiry_date, request.created_at)
    if request.expiry_date == expiry_date:
        return comment
    old_value = request.expiry_date.isoformat() if request.expiry_date else "—"
    new_value = expiry_date.isoformat()
    note = f"Срок действия: {old_value} → {new_value}"
    request.expiry_date = expiry_date
    if comment:
        return f"{comment}\n{note}"
    return note


def _fill_missing_approved_quantities(request: Request) -> None:
    for item in request.items:
        if item.quantity_approved is None:
            item.quantity_approved = item.quantity_requested


def _normative_quantity(item: RequestItem) -> Decimal:
    if item.quantity_approved is not None:
        return item.quantity_approved
    return item.quantity_requested


async def _ensure_normatives(db: AsyncSession, request: Request) -> None:
    if request.request_type != "normative":
        return
    if request.expiry_date is None:
        raise APIError(
            400,
            "VALIDATION_ERROR",
            "Для нормативного запроса отсутствует срок действия",
        )

    now = datetime.now(UTC)

    existing_result = await db.execute(
        select(Normative).where(
            Normative.request_id == request.id,
            Normative.deleted_at.is_(None),
        )
    )
    existing_normatives = list(existing_result.scalars().all())
    existing_by_key = {
        (n.product_code, n.warehouse_code): n for n in existing_normatives
    }

    items_by_key = {
        (item.product_code, item.warehouse_code): item for item in request.items
    }

    for (prod_code, wh_code), item in items_by_key.items():
        qty = _normative_quantity(item)
        category = (
            item.product.category.strip()
            if item.product and item.product.category
            else "A"
        )
        if (prod_code, wh_code) in existing_by_key:
            normative = existing_by_key[(prod_code, wh_code)]
            normative.quantity = qty
            normative.expiry_date = request.expiry_date
            normative.client_id = request.client_id
            normative.client_name = request.client_name
            normative.category = category
            normative.unit = item.unit
        else:
            prev_result = await db.execute(
                select(Normative).where(
                    Normative.product_code == prod_code,
                    Normative.warehouse_code == wh_code,
                    or_(
                        Normative.request_id.is_(None),
                        Normative.request_id != request.id,
                    ),
                    Normative.production_request_item_id.is_(None),
                    Normative.deleted_at.is_(None),
                    or_(
                        Normative.client_id == request.client_id,
                        Normative.client_id == SYSTEM_CLIENT_ID,
                    ),
                )
            )
            replaced_by_name: list[Normative] = []
            for prev_norm in prev_result.scalars().all():
                same_client = prev_norm.client_id == request.client_id
                by_name = (
                    not same_client
                    and prev_norm.client_id == SYSTEM_CLIENT_ID
                    and names_match(prev_norm.client_name, request.client_name)
                )
                if not same_client and not by_name:
                    continue
                prev_norm.deleted_at = now
                if by_name:
                    replaced_by_name.append(prev_norm)

            normative = Normative(
                request_id=request.id,
                product_code=prod_code,
                warehouse_code=wh_code,
                quantity=qty,
                unit=item.unit,
                client_id=request.client_id,
                client_name=request.client_name,
                expiry_date=request.expiry_date,
                category=category,
            )
            db.add(normative)
            await db.flush()
            for old in replaced_by_name:
                db.add(
                    Event(
                        event_type="normative_replaced_by_name",
                        request_id=request.id,
                        payload={
                            "old_normative_id": str(old.id),
                            "new_normative_id": str(normative.id),
                            "client_name": request.client_name,
                            "product_code": prod_code,
                            "warehouse_code": wh_code,
                        },
                        processed=False,
                    )
                )

    for (prod_code, wh_code), normative in existing_by_key.items():
        if (prod_code, wh_code) not in items_by_key:
            normative.deleted_at = now


def _next_status(stage: Stage, action: str, request: Request) -> str:
    if action == "reject":
        return "rejected"
    if stage == "pp":
        return "economy_check"
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
        if body.action == "approve":
            if body.items:
                await _apply_edits(db, request, body, user, comment)
            _fill_missing_approved_quantities(request)
            comment = _apply_expiry_update(
                request,
                body.expiry_date,
                comment,
                restrict_decrease=(
                    stage == "economy" and request.request_type == "normative"
                ),
            )

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
