"""Start date and overlapping commercial requests for a normative."""

from dataclasses import dataclass
from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import Date, and_, cast, func, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.normative import Normative
from app.models.request import Request


@dataclass(frozen=True)
class OverlappingRequest:
    id: UUID
    created_at: date
    expiry_date: date | None


def commercial_start_column():
    return func.coalesce(Normative.valid_from, cast(Normative.created_at, Date))


def commercial_active_on(on_date: date):
    """Commercial row has started. Excel batches use their own valid_from."""
    return and_(
        Normative.production_request_item_id.is_(None),
        commercial_start_column() <= on_date,
    )


def _calendar_date(value: datetime) -> date:
    if value.tzinfo is None:
        return value.date()
    return value.astimezone(UTC).date()


async def find_overlapping_requests(
    db: AsyncSession,
    *,
    client_id: UUID,
    positions: list[tuple[int, int]],
    exclude_request_id: UUID | None = None,
    on_date: date | None = None,
) -> list[OverlappingRequest]:
    """Active commercial requests of the client that contain these positions."""
    unique = list(dict.fromkeys(positions))
    if not unique:
        return []
    today = on_date or date.today()
    conditions = [
        Normative.client_id == client_id,
        Normative.deleted_at.is_(None),
        Normative.expiry_date >= today,
        Normative.request_id.is_not(None),
        commercial_active_on(today),
        tuple_(Normative.product_code, Normative.warehouse_code).in_(unique),
    ]
    if exclude_request_id is not None:
        conditions.append(Normative.request_id != exclude_request_id)
    rows = (
        await db.scalars(
            select(Normative)
            .options(selectinload(Normative.request))
            .where(*conditions)
        )
    ).all()
    found: dict[UUID, Request] = {}
    for row in rows:
        request = row.request
        if request is None or request.deleted_at is not None or row.request_id is None:
            continue
        found[row.request_id] = request
    ordered = sorted(found.values(), key=lambda item: item.created_at)
    return [
        OverlappingRequest(
            id=item.id,
            created_at=_calendar_date(item.created_at),
            expiry_date=item.expiry_date,
        )
        for item in ordered
    ]


async def complete_overlapping_requests(
    db: AsyncSession,
    request: Request,
    *,
    on_date: date | None = None,
) -> None:
    """End each overlapping request and all of its normatives on on_date."""
    today = on_date or date.today()
    positions = [(item.product_code, item.warehouse_code) for item in request.items]
    found = await find_overlapping_requests(
        db,
        client_id=request.client_id,
        positions=positions,
        exclude_request_id=request.id,
        on_date=today,
    )
    if not found:
        return
    ids = [item.id for item in found]
    requests = (await db.scalars(select(Request).where(Request.id.in_(ids)))).all()
    for old in requests:
        old.expiry_date = today
    normatives = (
        await db.scalars(
            select(Normative).where(
                Normative.request_id.in_(ids),
                Normative.deleted_at.is_(None),
            )
        )
    ).all()
    for normative in normatives:
        normative.expiry_date = today
