from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_roles
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.schemas.params import ParamsResponse, ParamsUpdate
from app.services import params as params_service

router = APIRouter(tags=["Параметры"])
LOGISTICS_ONLY = require_roles("logistics")


@router.get("/params", response_model=SuccessResponse[ParamsResponse])
async def get_params(
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[ParamsResponse]:
    return SuccessResponse(data=await params_service.get_params(db))


@router.get("/admin/params", response_model=SuccessResponse[ParamsResponse])
async def get_admin_params(
    _user: User = Depends(LOGISTICS_ONLY),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[ParamsResponse]:
    return SuccessResponse(data=await params_service.get_params(db))


@router.put("/admin/params", response_model=SuccessResponse[ParamsResponse])
async def update_admin_params(
    body: ParamsUpdate,
    current_user: User = Depends(LOGISTICS_ONLY),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[ParamsResponse]:
    data = await params_service.update_params(db, body, current_user.id)
    return SuccessResponse(data=data)
