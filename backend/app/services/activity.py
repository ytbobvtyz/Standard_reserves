"""Journal of mutating actions, stored in events."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import String, and_, cast, false, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import APIError
from app.core.pagination import paginate
from app.models.event import Event
from app.models.user import User
from app.schemas.activity import ActivityEvent, ActivityUser


def record_activity(
    db: AsyncSession,
    *,
    event_type: str,
    user: User | None = None,
    user_id: UUID | None = None,
    entity_type: str | None = None,
    entity_id: UUID | None = None,
    request_id: UUID | None = None,
    label: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    stored = dict(details or {})
    if label:
        stored["label"] = label
    actor_id = user.id if user is not None else user_id
    db.add(
        Event(
            event_type=event_type,
            user_id=actor_id,
            entity_type=entity_type,
            entity_id=entity_id,
            request_id=request_id,
            details=stored,
            payload=dict(stored),
            processed=False,
        )
    )


def record_request_activity(
    db: AsyncSession,
    *,
    event_type: str,
    user: User,
    request: Any,
    details: dict[str, Any] | None = None,
) -> None:
    extra = {
        "request_type": request.request_type,
        "status": request.status,
    }
    if details:
        extra.update(details)
    record_activity(
        db,
        event_type=event_type,
        user=user,
        entity_type="request",
        entity_id=request.id,
        request_id=request.id,
        label=f"Запрос ({request.client_name})",
        details=extra,
    )


async def commit_activity(db: AsyncSession, **kwargs: Any) -> None:
    record_activity(db, **kwargs)
    await db.commit()


def _request_number_clause(raw: str | None):
    if raw is None:
        return None
    value = raw.strip().lower().lstrip("№").lstrip("#").replace(" ", "")
    if not value:
        return None
    compact = value.replace("-", "")
    if not compact or any(char not in "0123456789abcdef" for char in compact):
        return false()
    if len(compact) == 32:
        value = str(UUID(hex=compact))
    pattern = f"{value}%"
    request_text = cast(Event.request_id, String)
    entity_text = cast(Event.entity_id, String)
    return or_(
        request_text.ilike(pattern),
        and_(Event.entity_type == "request", entity_text.ilike(pattern)),
    )


def _bounds(date_from: date, date_to: date) -> tuple[datetime, datetime]:
    if date_from > date_to:
        raise APIError(
            400,
            "VALIDATION_ERROR",
            "date_from не может быть позже date_to",
        )
    start = datetime.combine(date_from, time.min, tzinfo=UTC)
    end = datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=UTC)
    return start, end


def _to_item(event: Event, actor: User | None) -> ActivityEvent:
    body = event.details if isinstance(event.details, dict) else None
    if body is None and isinstance(event.payload, dict):
        body = event.payload
    details = dict(body or {})
    label = details.get("label")
    user = None
    if actor is not None:
        user = ActivityUser(id=actor.id, full_name=actor.full_name, role=actor.role)
    return ActivityEvent(
        id=event.id,
        created_at=event.created_at,
        user=user,
        event_type=event.event_type,
        entity_type=event.entity_type,
        entity_id=event.entity_id,
        entity_label=label if isinstance(label, str) else None,
        details=details,
    )


async def list_activity(
    db: AsyncSession,
    *,
    date_from: date,
    date_to: date,
    user_id: UUID | None,
    event_type: str | None,
    entity_type: str | None,
    request_number: str | None,
    page: int,
    limit: int,
) -> tuple[list[ActivityEvent], int]:
    start, end = _bounds(date_from, date_to)
    conditions = [Event.created_at >= start, Event.created_at < end]
    if user_id is not None:
        conditions.append(Event.user_id == user_id)
    if event_type:
        conditions.append(Event.event_type == event_type)
    if entity_type:
        conditions.append(Event.entity_type == entity_type)
    number_clause = _request_number_clause(request_number)
    if number_clause is not None:
        conditions.append(number_clause)

    total = await db.scalar(select(func.count()).select_from(Event).where(*conditions))
    result = await db.execute(
        paginate(
            select(Event, User)
            .outerjoin(User, User.id == Event.user_id)
            .where(*conditions)
            .order_by(Event.created_at.desc(), Event.id.desc()),
            page,
            limit,
        )
    )
    items = [_to_item(event, actor) for event, actor in result.all()]
    return items, int(total or 0)
