from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.schemas.reference import RelatedProductsData
from app.services.references import get_related_products

router = APIRouter(tags=["Продукты"])


@router.get(
    "/products/{code}/related",
    response_model=SuccessResponse[RelatedProductsData],
)
async def list_related_products(
    code: int,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[RelatedProductsData]:
    data = await get_related_products(db, code)
    return SuccessResponse(data=data)
