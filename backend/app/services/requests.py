from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import APIError
from app.models.object import Object
from app.models.product import Product
from app.models.request import Request
from app.models.request_item import RequestItem
from app.models.request_item_history import RequestItemHistory
from app.models.user import User
from app.schemas.request import (
    ApprovalActor,
    HistoryChangedBy,
    ProductBrief,
    RequestApprovals,
    RequestCreate,
    RequestCreated,
    RequestDetail,
    RequestHistoryEntry,
    RequestItemCreate,
    RequestItemCreated,
    RequestItemDetail,
    RequestItemHistoryEntry,
    RequestListItem,
    RequestUpdate,
    WarehouseBrief,
)
from app.schemas.user import UserBrief

VIEW_ALL_ROLES = {"pp", "economist", "logistics"}


def can_view_request(user: User, request: Request) -> bool:
    if user.role in VIEW_ALL_ROLES:
        return True
    return request.initiator_id == user.id


def can_create_request(user: User, request_type: str) -> bool:
    if user.role == "commercial":
        return True
    return user.role == "logistics" and request_type == "one_time"


def apply_own_requests_scope(user: User) -> UUID | None:
    if user.role in VIEW_ALL_ROLES:
        return None
    return user.id


async def validate_items(db: AsyncSession, items: list[RequestItemCreate]) -> None:
    pairs = [(item.product_code, item.warehouse_code) for item in items]
    if len(pairs) != len(set(pairs)):
        raise APIError(
            400,
            "DUPLICATE_ITEMS",
            "Позиции с одинаковым продуктом и складом недопустимы",
        )

    product_codes = {item.product_code for item in items}
    products = (
        (
            await db.execute(
                select(Product).where(
                    Product.code.in_(product_codes),
                    Product.deleted_at.is_(None),
                )
            )
        )
        .scalars()
        .all()
    )
    products_by_code = {product.code: product for product in products}
    for code in product_codes:
        product = products_by_code.get(code)
        if product is None:
            raise APIError(400, "PRODUCT_NOT_FOUND", f"Продукт {code} не найден")
        if not product.is_active:
            raise APIError(400, "PRODUCT_INACTIVE", f"Продукт {code} неактивен")

    warehouse_codes = {item.warehouse_code for item in items}
    warehouses = (
        (
            await db.execute(
                select(Object).where(
                    Object.code.in_(warehouse_codes),
                    Object.deleted_at.is_(None),
                )
            )
        )
        .scalars()
        .all()
    )
    warehouses_by_code = {warehouse.code: warehouse for warehouse in warehouses}
    for code in warehouse_codes:
        warehouse = warehouses_by_code.get(code)
        if warehouse is None:
            raise APIError(400, "OBJECT_NOT_FOUND", f"Объект {code} не найден")
        if warehouse.type != "warehouse":
            raise APIError(
                400,
                "INVALID_WAREHOUSE",
                f"Объект {code} не является складом",
            )
        if not warehouse.is_active:
            raise APIError(400, "OBJECT_INACTIVE", f"Объект {code} неактивен")


def _build_items(items: list[RequestItemCreate]) -> list[RequestItem]:
    return [
        RequestItem(
            product_code=item.product_code,
            warehouse_code=item.warehouse_code,
            quantity_requested=item.quantity_requested,
            unit=item.unit,
            comment=item.comment,
        )
        for item in items
    ]


def _created_schema(request: Request) -> RequestCreated:
    return RequestCreated(
        id=request.id,
        request_type=request.request_type,
        status=request.status,
        client_name=request.client_name,
        initiator_id=request.initiator_id,
        expiry_date=request.expiry_date,
        items=[RequestItemCreated.model_validate(item) for item in request.items],
        created_at=request.created_at,
    )


def to_list_item(request: Request) -> RequestListItem:
    total = sum(
        (item.quantity_requested for item in request.items),
        Decimal("0"),
    )
    return RequestListItem(
        id=request.id,
        request_type=request.request_type,
        status=request.status,
        client_name=request.client_name,
        initiator=UserBrief.model_validate(request.initiator),
        items_count=len(request.items),
        total_quantity=total,
        expiry_date=request.expiry_date,
        created_at=request.created_at,
    )


def _history(request: Request) -> list[RequestHistoryEntry]:
    entries = [
        RequestHistoryEntry(
            timestamp=request.created_at,
            action="created",
            user_name=request.initiator.full_name if request.initiator else None,
            comment=request.initiator_comment,
        )
    ]
    if request.status != "draft":
        entries.append(
            RequestHistoryEntry(
                timestamp=request.updated_at,
                action="submitted",
                user_name=request.initiator.full_name if request.initiator else None,
            )
        )
    if request.pp_approved_at:
        entries.append(
            RequestHistoryEntry(
                timestamp=request.pp_approved_at,
                action=request.pp_action or "pp_reviewed",
                user_name=(
                    request.pp_approver.full_name if request.pp_approver else None
                ),
                comment=request.comment_pp,
            )
        )
    if request.economy_approved_at:
        entries.append(
            RequestHistoryEntry(
                timestamp=request.economy_approved_at,
                action=request.economy_action or "economy_reviewed",
                user_name=(
                    request.economy_approver.full_name
                    if request.economy_approver
                    else None
                ),
                comment=request.comment_economy,
            )
        )
    return entries


def to_detail(request: Request) -> RequestDetail:
    return RequestDetail(
        id=request.id,
        request_type=request.request_type,
        status=request.status,
        client_name=request.client_name,
        initiator=UserBrief.model_validate(request.initiator),
        initiator_comment=request.initiator_comment,
        comment_pp=request.comment_pp,
        comment_economy=request.comment_economy,
        expiry_date=request.expiry_date,
        items=[
            RequestItemDetail(
                id=item.id,
                product=ProductBrief(
                    code=item.product.code,
                    name=item.product.name,
                    category=item.product.category.strip(),
                    weight_kg=item.product.weight_kg,
                ),
                warehouse=WarehouseBrief.model_validate(item.warehouse),
                quantity_requested=item.quantity_requested,
                quantity_approved=item.quantity_approved,
                unit=item.unit,
                comment=item.comment,
            )
            for item in request.items
        ],
        approvals=RequestApprovals(
            pp=ApprovalActor(
                approved_at=request.pp_approved_at,
                approved_by=(
                    UserBrief.model_validate(request.pp_approver)
                    if request.pp_approver
                    else None
                ),
                action=request.pp_action,
            ),
            economy=ApprovalActor(
                approved_at=request.economy_approved_at,
                approved_by=(
                    UserBrief.model_validate(request.economy_approver)
                    if request.economy_approver
                    else None
                ),
                action=request.economy_action,
            ),
        ),
        history=_history(request),
        created_at=request.created_at,
        updated_at=request.updated_at,
    )


DETAIL_OPTIONS = (
    selectinload(Request.items).selectinload(RequestItem.product),
    selectinload(Request.items).selectinload(RequestItem.warehouse),
    selectinload(Request.initiator),
    selectinload(Request.pp_approver),
    selectinload(Request.economy_approver),
)

LIST_OPTIONS = (
    selectinload(Request.items),
    selectinload(Request.initiator),
)


async def load_request(
    db: AsyncSession,
    request_id: UUID,
    *,
    for_detail: bool = True,
) -> Request:
    options = DETAIL_OPTIONS if for_detail else LIST_OPTIONS
    result = await db.execute(
        select(Request)
        .options(*options)
        .where(Request.id == request_id, Request.deleted_at.is_(None))
    )
    request = result.scalar_one_or_none()
    if request is None:
        raise APIError(404, "NOT_FOUND", "Запрос не найден")
    return request


async def get_visible_request(
    db: AsyncSession, request_id: UUID, user: User
) -> Request:
    request = await load_request(db, request_id)
    if not can_view_request(user, request):
        raise APIError(403, "FORBIDDEN", "Недостаточно прав")
    return request


async def get_request_item_history(
    db: AsyncSession, request_id: UUID, user: User
) -> list[RequestItemHistoryEntry]:
    await get_visible_request(db, request_id, user)
    result = await db.execute(
        select(RequestItemHistory)
        .options(selectinload(RequestItemHistory.changed_by_user))
        .join(RequestItem, RequestItem.id == RequestItemHistory.request_item_id)
        .where(RequestItem.request_id == request_id)
        .order_by(RequestItemHistory.changed_at.asc())
    )
    entries: list[RequestItemHistoryEntry] = []
    for row in result.scalars().unique().all():
        changer = row.changed_by_user
        entries.append(
            RequestItemHistoryEntry(
                item_id=row.request_item_id,
                field_name=row.field_name,
                old_value=row.old_value,
                new_value=row.new_value,
                changed_by=HistoryChangedBy(
                    id=changer.id if changer else row.changed_by,
                    full_name=changer.full_name if changer else "",
                ),
                changed_at=row.changed_at,
                comment=row.comment,
            )
        )
    return entries


def ensure_draft_owner(request: Request, user: User) -> None:
    if request.initiator_id != user.id:
        raise APIError(403, "FORBIDDEN", "Недостаточно прав")
    if request.status != "draft":
        raise APIError(
            400,
            "INVALID_STATUS",
            "Действие доступно только для черновика",
        )


async def create_request(
    db: AsyncSession, user: User, body: RequestCreate
) -> RequestCreated:
    if not can_create_request(user, body.request_type):
        raise APIError(403, "FORBIDDEN", "Недостаточно прав")
    if body.request_type == "normative" and body.expiry_date is None:
        raise APIError(
            400,
            "VALIDATION_ERROR",
            "Для нормативного запроса укажите срок действия",
        )
    await validate_items(db, body.items)

    request = Request(
        request_type=body.request_type,
        status="draft",
        client_name=body.client_name,
        initiator_id=user.id,
        initiator_comment=body.comment,
        expiry_date=body.expiry_date,
        items=_build_items(body.items),
    )
    db.add(request)
    await db.commit()
    request = await load_request(db, request.id)
    return _created_schema(request)


async def update_draft(
    db: AsyncSession, request: Request, body: RequestUpdate
) -> Request:
    if body.client_name is not None:
        request.client_name = body.client_name
    if body.comment is not None:
        request.initiator_comment = body.comment
    if body.expiry_date is not None:
        request.expiry_date = body.expiry_date
    if body.items is not None:
        await validate_items(db, body.items)
        request.items.clear()
        await db.flush()
        request.items.extend(_build_items(body.items))
    await db.commit()
    return await load_request(db, request.id, for_detail=False)


async def delete_draft(db: AsyncSession, request: Request) -> None:
    request.deleted_at = datetime.now(UTC)
    await db.commit()


async def submit_draft(db: AsyncSession, request: Request) -> Request:
    request.status = "pp_approved"
    await db.commit()
    return await load_request(db, request.id, for_detail=False)
