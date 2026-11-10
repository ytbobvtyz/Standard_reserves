from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_roles
from app.models.user import User
from app.schemas.activity import ActivityEvent
from app.schemas.common import PaginatedResponse, PaginationMeta
from app.services.activity import list_activity

router = APIRouter(prefix="/admin", tags=["Администрирование"])
ADMIN_ONLY = require_roles("admin")


@router.get("/audit", response_model=PaginatedResponse[list[ActivityEvent]])
async def get_audit(
    date_from: date = Query(...),
    date_to: date = Query(...),
    user_id: UUID | None = Query(default=None),
    event_type: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    request_number: str | None = Query(default=None, max_length=40),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    _user: User = Depends(ADMIN_ONLY),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[list[ActivityEvent]]:
    items, total = await list_activity(
        db,
        date_from=date_from,
        date_to=date_to,
        user_id=user_id,
        event_type=event_type,
        entity_type=entity_type,
        request_number=request_number,
        page=page,
        limit=limit,
    )
    return PaginatedResponse(
        data=items,
        meta=PaginationMeta(page=page, limit=limit, total=total),
    )
