from datetime import UTC, date, datetime
from decimal import Decimal
from io import BytesIO
from uuid import UUID

from openpyxl import Workbook
from sqlalchemy import Select, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import APIError
from app.models.request import Request
from app.models.request_item import RequestItem
from app.models.user import User
from app.schemas.logistics import (
    ExecuteOneTimeData,
    ExecuteOneTimeRequest,
    OneTimeInitiator,
    OneTimeItem,
    OneTimeListItem,
)
from app.schemas.user import UserBrief

ONE_TIME_TYPE = "one_time"
EXECUTABLE_STATUS = "approved"


def _item_quantity(item: RequestItem) -> Decimal:
    if item.quantity_approved is not None:
        return item.quantity_approved
    return item.quantity_requested


def to_list_item(request: Request) -> OneTimeListItem:
    return OneTimeListItem(
        id=request.id,
        client_name=request.client_name,
        status=request.status,
        initiator=UserBrief.model_validate(request.initiator),
        items=[
            OneTimeItem(
                product_code=item.product_code,
                product_name=item.product.name,
                warehouse_code=item.warehouse_code,
                warehouse_name=item.warehouse.name,
                quantity=_item_quantity(item),
                unit=item.unit,
            )
            for item in request.items
        ],
        created_at=request.created_at,
        order_number=request.order_number,
        executed_at=request.executed_at,
    )


def _list_options():
    return (
        selectinload(Request.initiator),
        selectinload(Request.items).selectinload(RequestItem.product),
        selectinload(Request.items).selectinload(RequestItem.warehouse),
    )


def build_list_query(
    *,
    warehouse_code: int | None = None,
    client_name: str | None = None,
    initiator_id: UUID | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    status: str | None = None,
) -> tuple[list, Select]:
    conditions = [
        Request.deleted_at.is_(None),
        Request.request_type == ONE_TIME_TYPE,
    ]
    if warehouse_code is not None:
        conditions.append(
            exists(
                select(RequestItem.id).where(
                    RequestItem.request_id == Request.id,
                    RequestItem.warehouse_code == warehouse_code,
                )
            )
        )
    if client_name and client_name.strip():
        conditions.append(Request.client_name.ilike(f"%{client_name.strip()}%"))
    if initiator_id is not None:
        conditions.append(Request.initiator_id == initiator_id)
    if from_date:
        conditions.append(func.date(Request.created_at) >= from_date)
    if to_date:
        conditions.append(func.date(Request.created_at) <= to_date)
    if status:
        conditions.append(Request.status == status)
    stmt = (
        select(Request)
        .options(*_list_options())
        .where(*conditions)
        .order_by(Request.created_at.desc())
    )
    return conditions, stmt


async def list_one_time_requests(
    db: AsyncSession,
    *,
    warehouse_code: int | None = None,
    client_name: str | None = None,
    initiator_id: UUID | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    status: str | None = None,
    page: int = 1,
    limit: int = 50,
) -> tuple[list[OneTimeListItem], int]:
    conditions, stmt = build_list_query(
        warehouse_code=warehouse_code,
        client_name=client_name,
        initiator_id=initiator_id,
        from_date=from_date,
        to_date=to_date,
        status=status,
    )
    total = await db.scalar(
        select(func.count()).select_from(Request).where(*conditions)
    )
    result = await db.execute(stmt.offset((page - 1) * limit).limit(limit))
    requests = result.scalars().unique().all()
    return [to_list_item(item) for item in requests], total or 0


async def list_initiators(db: AsyncSession) -> list[OneTimeInitiator]:
    result = await db.execute(
        select(User)
        .join(Request, Request.initiator_id == User.id)
        .where(
            Request.request_type == ONE_TIME_TYPE,
            Request.deleted_at.is_(None),
            User.deleted_at.is_(None),
        )
        .distinct()
        .order_by(User.full_name)
    )
    return [
        OneTimeInitiator(id=user.id, username=user.username, full_name=user.full_name)
        for user in result.scalars().all()
    ]


async def list_clients(db: AsyncSession) -> list[str]:
    result = await db.execute(
        select(Request.client_name)
        .where(
            Request.request_type == ONE_TIME_TYPE,
            Request.deleted_at.is_(None),
        )
        .distinct()
        .order_by(Request.client_name)
    )
    return [name for name in result.scalars().all() if name]


async def load_one_time_request(db: AsyncSession, request_id: UUID) -> Request:
    result = await db.execute(
        select(Request)
        .options(*_list_options())
        .where(Request.id == request_id, Request.deleted_at.is_(None))
    )
    request = result.scalar_one_or_none()
    if request is None:
        raise APIError(404, "NOT_FOUND", "Запрос не найден")
    if request.request_type != ONE_TIME_TYPE:
        raise APIError(400, "INVALID_TYPE", "Запрос не является разовым перемещением")
    return request


async def execute_one_time(
    db: AsyncSession,
    request_id: UUID,
    body: ExecuteOneTimeRequest,
    current_user: User,
) -> ExecuteOneTimeData:
    request = await load_one_time_request(db, request_id)
    if request.status != EXECUTABLE_STATUS:
        raise APIError(
            400,
            "INVALID_STATUS",
            "Исполнить можно только согласованный разовый запрос",
        )

    order_number = body.order_number.strip()
    if not order_number:
        raise APIError(400, "VALIDATION_ERROR", "Номер разнарядки обязателен")

    comment = body.comment.strip() if body.comment else None
    now = datetime.now(UTC)
    request.status = "executed"
    request.executed_at = now
    request.executed_by = current_user.id
    request.order_number = order_number
    request.executed_comment = comment or None
    await db.commit()
    await db.refresh(request)
    return ExecuteOneTimeData(
        id=request.id,
        status=request.status,
        executed_at=request.executed_at,
        executed_by=request.executed_by,
        order_number=request.order_number,
        executed_comment=request.executed_comment,
    )


async def export_one_time_excel(db: AsyncSession, request_id: UUID) -> bytes:
    request = await load_one_time_request(db, request_id)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Разовое перемещение"
    sheet.append(
        [
            "Артикул",
            "Название",
            "Склад",
            "Количество",
            "Ед",
            "Клиент",
            "Заявитель",
            "Статус",
        ]
    )
    initiator_name = request.initiator.full_name if request.initiator else ""
    for item in request.items:
        sheet.append(
            [
                item.product_code,
                item.product.name,
                item.warehouse.name,
                float(_item_quantity(item)),
                item.unit,
                request.client_name,
                initiator_name,
                request.status,
            ]
        )
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
