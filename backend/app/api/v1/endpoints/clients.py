from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_roles
from app.core.exceptions import APIError
from app.models.user import User
from app.schemas.client import (
    ClientCreate,
    ClientListItem,
    ClientUpdate,
    ClientUploadPreview,
    ClientUploadResult,
)
from app.schemas.common import MessageResponse, PaginatedResponse, SuccessResponse
from app.services import clients as service

router = APIRouter(prefix="/references/clients", tags=["Справочники"])
CLIENT_EDITORS = require_roles("commercial", "logistics", "pp", "economist")
LOGISTICS = require_roles("logistics")
MAX_UPLOAD_SIZE = 10 * 1024 * 1024


@router.get("", response_model=PaginatedResponse[list[ClientListItem]])
async def list_clients(
    q: str | None = Query(default=None),
    department_id: UUID | None = Query(default=None),
    is_active: bool | None = Query(default=True),
    include_inactive: bool = Query(default=False),
    include_deleted: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[list[ClientListItem]]:
    items, meta = await service.list_clients(
        db,
        q=q,
        department_id=department_id,
        is_active=is_active,
        include_inactive=include_inactive,
        include_deleted=include_deleted,
        page=page,
        limit=limit,
    )
    return PaginatedResponse(data=items, meta=meta)


@router.get("/template")
async def download_template(
    _user: User = Depends(LOGISTICS),
) -> Response:
    content = service.build_template_xlsx()
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="clients-template.xlsx"'},
    )


@router.get("/export")
async def export_clients(
    _user: User = Depends(LOGISTICS),
    db: AsyncSession = Depends(get_db),
) -> Response:
    content = await service.export_clients_xlsx(db)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="clients.xlsx"'},
    )


@router.post(
    "/preview",
    response_model=SuccessResponse[ClientUploadPreview],
)
async def preview_clients(
    file: UploadFile = File(...),
    _user: User = Depends(LOGISTICS),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[ClientUploadPreview]:
    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise APIError(400, "INVALID_FILE", "Размер файла не должен превышать 10 МБ")
    data = await service.preview_clients_xlsx(
        db, content, file.filename or "clients.xlsx"
    )
    return SuccessResponse(data=data)


@router.post(
    "/upload",
    response_model=SuccessResponse[ClientUploadResult],
)
async def upload_clients(
    file: UploadFile = File(...),
    _user: User = Depends(LOGISTICS),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[ClientUploadResult]:
    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise APIError(400, "INVALID_FILE", "Размер файла не должен превышать 10 МБ")
    data = await service.upload_clients_xlsx(
        db, content, file.filename or "clients.xlsx"
    )
    return SuccessResponse(data=data)


@router.get("/{client_id}", response_model=SuccessResponse[ClientListItem])
async def get_client(
    client_id: UUID,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[ClientListItem]:
    client = await service.get_client(db, client_id)
    return SuccessResponse(data=service.to_list_item(client))


@router.post(
    "",
    status_code=201,
    response_model=SuccessResponse[ClientListItem],
)
async def create_client(
    body: ClientCreate,
    user: User = Depends(CLIENT_EDITORS),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[ClientListItem]:
    return SuccessResponse(data=await service.create_client(db, user, body))


@router.put("/{client_id}", response_model=SuccessResponse[ClientListItem])
async def update_client(
    client_id: UUID,
    body: ClientUpdate,
    _user: User = Depends(LOGISTICS),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[ClientListItem]:
    return SuccessResponse(data=await service.update_client(db, client_id, body))


@router.delete("/{client_id}", response_model=MessageResponse)
async def delete_client(
    client_id: UUID,
    _user: User = Depends(LOGISTICS),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    await service.delete_client(db, client_id)
    return MessageResponse(message="Клиент удалён")
