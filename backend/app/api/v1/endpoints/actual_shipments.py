from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_roles
from app.core.exceptions import APIError
from app.models.user import User
from app.schemas.actual_shipments import (
    ActualShipmentListItem,
    ActualShipmentUploadResult,
)
from app.schemas.common import PaginatedResponse, PaginationMeta, SuccessResponse
from app.services import actual_shipments as service

router = APIRouter(
    prefix="/logistics/actual-shipments", tags=["Логистика — реализация"]
)
SHIPMENT_EDITORS = require_roles("logistics", "economist", "pp")
MAX_UPLOAD_SIZE = 10 * 1024 * 1024


@router.get("", response_model=PaginatedResponse[list[ActualShipmentListItem]])
async def list_shipments(
    client_id: UUID | None = Query(default=None),
    product_code: int | None = Query(default=None),
    warehouse_code: int | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    _current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[list[ActualShipmentListItem]]:
    items, total = await service.list_shipments(
        db,
        client_id=client_id,
        product_code=product_code,
        warehouse_code=warehouse_code,
        date_from=date_from,
        date_to=date_to,
        page=page,
        limit=limit,
    )
    return PaginatedResponse(
        data=items,
        meta=PaginationMeta(page=page, limit=limit, total=total),
    )


@router.get("/template")
async def download_template(
    _current_user: User = Depends(SHIPMENT_EDITORS),
) -> Response:
    content = service.build_template_xlsx()
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": (
                'attachment; filename="actual-shipments-template.xlsx"'
            )
        },
    )


@router.post("/upload", response_model=SuccessResponse[ActualShipmentUploadResult])
async def upload_shipments(
    file: UploadFile = File(...),
    confirm: bool = Query(default=False),
    current_user: User = Depends(SHIPMENT_EDITORS),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[ActualShipmentUploadResult]:
    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise APIError(400, "INVALID_FILE", "Размер файла не должен превышать 10 МБ")
    data = await service.upload_shipments(
        db,
        content,
        file.filename or "actual-shipments.xlsx",
        user_id=current_user.id,
        confirm=confirm,
    )
    return SuccessResponse(data=data)
