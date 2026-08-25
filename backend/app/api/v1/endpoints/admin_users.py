from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_roles
from app.models.user import User
from app.schemas.admin import (
    DepartmentOption,
    PasswordResetResponse,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from app.schemas.common import (
    MessageResponse,
    PaginatedResponse,
    PaginationMeta,
    SuccessResponse,
)
from app.services import admin_users as admin_users_service

router = APIRouter(prefix="/admin", tags=["Администрирование"])
LOGISTICS_ONLY = require_roles("logistics")


@router.get("/users", response_model=PaginatedResponse[list[UserResponse]])
async def list_users(
    search: str | None = Query(default=None),
    role: Literal["commercial", "pp", "economist", "logistics", "guest"] | None = Query(
        default=None
    ),
    department_id: UUID | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    deleted: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    _user: User = Depends(LOGISTICS_ONLY),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[list[UserResponse]]:
    data, total = await admin_users_service.list_users(
        db,
        search=search,
        role=role,
        department_id=department_id,
        is_active=is_active,
        deleted=deleted,
        page=page,
        limit=limit,
    )
    return PaginatedResponse(
        data=data,
        meta=PaginationMeta(page=page, limit=limit, total=total),
    )


@router.post(
    "/users",
    response_model=SuccessResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_user(
    body: UserCreate,
    current_user: User = Depends(LOGISTICS_ONLY),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[UserResponse]:
    created = await admin_users_service.create_user(db, body, current_user)
    return SuccessResponse(data=created)


@router.get("/departments", response_model=SuccessResponse[list[DepartmentOption]])
async def list_departments(
    _user: User = Depends(LOGISTICS_ONLY),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[list[DepartmentOption]]:
    return SuccessResponse(data=await admin_users_service.list_departments(db))


@router.get("/users/{user_id}", response_model=SuccessResponse[UserResponse])
async def get_user(
    user_id: UUID,
    _user: User = Depends(LOGISTICS_ONLY),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[UserResponse]:
    return SuccessResponse(data=await admin_users_service.get_user(db, user_id))


@router.put("/users/{user_id}", response_model=SuccessResponse[UserResponse])
async def update_user(
    user_id: UUID,
    body: UserUpdate,
    current_user: User = Depends(LOGISTICS_ONLY),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[UserResponse]:
    updated = await admin_users_service.update_user(db, user_id, body, current_user)
    return SuccessResponse(data=updated)


@router.delete("/users/{user_id}", response_model=MessageResponse)
async def delete_user(
    user_id: UUID,
    current_user: User = Depends(LOGISTICS_ONLY),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    await admin_users_service.delete_user(db, user_id, current_user)
    return MessageResponse(message="Пользователь удален")


@router.post(
    "/users/{user_id}/reset-password",
    response_model=SuccessResponse[PasswordResetResponse],
)
async def reset_password(
    user_id: UUID,
    current_user: User = Depends(LOGISTICS_ONLY),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[PasswordResetResponse]:
    new_password = await admin_users_service.reset_password(db, user_id, current_user)
    return SuccessResponse(data=PasswordResetResponse(new_password=new_password))
