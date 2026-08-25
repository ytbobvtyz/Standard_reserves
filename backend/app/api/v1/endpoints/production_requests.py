from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_roles
from app.core.exceptions import APIError
from app.models.user import User
from app.schemas.common import MessageResponse, PaginatedResponse, SuccessResponse
from app.schemas.production_request import (
    ProductionRequestDatesUpdate,
    ProductionRequestDetail,
    ProductionRequestListItem,
    ProductionRequestUploadOptions,
    ProductionRequestUploadResult,
)
from app.services import production_requests as service

router = APIRouter(prefix="/production-requests", tags=["Производственные запросы"])
MANAGE_PRODUCTION_REQUESTS = require_roles("logistics", "economist", "pp")
MAX_UPLOAD_SIZE = 10 * 1024 * 1024


@router.get(
    "",
    response_model=PaginatedResponse[list[ProductionRequestListItem]],
)
async def list_production_requests(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    _current_user: User = Depends(MANAGE_PRODUCTION_REQUESTS),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[list[ProductionRequestListItem]]:
    items, meta = await service.list_batches(db, page=page, limit=limit)
    return PaginatedResponse(data=items, meta=meta)


@router.get("/template")
async def download_production_request_template(
    _current_user: User = Depends(MANAGE_PRODUCTION_REQUESTS),
) -> Response:
    return Response(
        content=service.build_template_xlsx(),
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": (
                'attachment; filename="production_normatives_template.xlsx"'
            )
        },
    )


@router.post(
    "/upload",
    status_code=201,
    response_model=SuccessResponse[ProductionRequestUploadResult],
)
async def upload_production_request(
    file: UploadFile = File(...),
    valid_from: date = Form(...),
    valid_to: date = Form(...),
    client_name: str | None = Form(default=None),
    current_user: User = Depends(MANAGE_PRODUCTION_REQUESTS),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[ProductionRequestUploadResult]:
    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise APIError(400, "INVALID_FILE", "Размер файла не должен превышать 10 МБ")
    if valid_to < valid_from:
        raise APIError(
            400,
            "INVALID_DATES",
            "Дата окончания не может быть раньше даты начала",
        )
    options = ProductionRequestUploadOptions(
        client_name=client_name,
        valid_from=valid_from,
        valid_to=valid_to,
    )
    return SuccessResponse(
        data=await service.upload_batch(
            db,
            content=content,
            filename=file.filename or "normatives.xlsx",
            user=current_user,
            options=options,
        )
    )


@router.patch(
    "/{production_request_id}/dates",
    response_model=SuccessResponse[ProductionRequestDetail],
)
async def update_production_request_dates(
    production_request_id: UUID,
    body: ProductionRequestDatesUpdate,
    _current_user: User = Depends(MANAGE_PRODUCTION_REQUESTS),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[ProductionRequestDetail]:
    return SuccessResponse(
        data=await service.update_dates(
            db,
            batch_id=production_request_id,
            body=body,
        )
    )


@router.delete(
    "/{production_request_id}",
    response_model=MessageResponse,
)
async def delete_production_request(
    production_request_id: UUID,
    _current_user: User = Depends(MANAGE_PRODUCTION_REQUESTS),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    await service.delete_batch(db, batch_id=production_request_id)
    return MessageResponse(message="Партия загрузки удалена")
