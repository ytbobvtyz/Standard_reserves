from typing import Literal

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy import Select, String, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db, require_roles
from app.core.exceptions import APIError
from app.models.object import Object
from app.models.product import Product
from app.models.user import User
from app.schemas.common import (
    MessageResponse,
    PaginatedResponse,
    PaginationMeta,
    SuccessResponse,
)
from app.schemas.reference import (
    ObjectListItem,
    ProductDetail,
    ProductListItem,
    ProductUpdate,
    ProductUploadResult,
    UserReference,
)
from app.services import products_admin
from app.services.references import to_product_detail, to_product_list_item

router = APIRouter(prefix="/references", tags=["Справочники"])
PRODUCT_MANAGERS = require_roles("pp", "economist", "logistics")


def _paginate(stmt: Select, page: int, limit: int) -> Select:
    return stmt.offset((page - 1) * limit).limit(limit)


@router.get("/products", response_model=PaginatedResponse[list[ProductListItem]])
async def list_products(
    search: str | None = Query(default=None),
    category: Literal["A", "B", "C"] | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[list[ProductListItem]]:
    conditions = [Product.deleted_at.is_(None)]
    if search:
        term = f"%{search.strip()}%"
        search_filters = [
            Product.name.ilike(term),
            cast(Product.code, String).ilike(term),
        ]
        if search.strip().isdigit():
            search_filters.append(Product.code == int(search.strip()))
        conditions.append(or_(*search_filters))
    if category:
        conditions.append(Product.category == category)
    if is_active is not None:
        conditions.append(Product.is_active == is_active)

    total = await db.scalar(
        select(func.count()).select_from(Product).where(*conditions)
    )
    result = await db.execute(
        _paginate(
            select(Product)
            .options(selectinload(Product.plant))
            .where(*conditions)
            .order_by(Product.code),
            page,
            limit,
        )
    )
    products = result.scalars().all()
    return PaginatedResponse(
        data=[to_product_list_item(product) for product in products],
        meta=PaginationMeta(page=page, limit=limit, total=total or 0),
    )


@router.get("/products/template")
async def download_products_template(
    _user: User = Depends(PRODUCT_MANAGERS),
) -> Response:
    content = products_admin.build_template_xlsx()
    return Response(
        content=content,
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": 'attachment; filename="products_template.xlsx"'
        },
    )


@router.post(
    "/products/upload",
    response_model=SuccessResponse[ProductUploadResult],
)
async def upload_products(
    file: UploadFile = File(...),
    current_user: User = Depends(PRODUCT_MANAGERS),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[ProductUploadResult]:
    content = await file.read()
    data = await products_admin.upload_products(
        db,
        current_user,
        content,
        file.filename or "products.xlsx",
    )
    return SuccessResponse(data=data)


@router.get(
    "/products/{code}/edit",
    response_model=SuccessResponse[ProductDetail],
)
async def get_product_for_edit(
    code: int,
    _user: User = Depends(PRODUCT_MANAGERS),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[ProductDetail]:
    data = await products_admin.get_product_for_edit(db, code)
    return SuccessResponse(data=data)


@router.put(
    "/products/{code}",
    response_model=SuccessResponse[ProductDetail],
)
async def update_product(
    code: int,
    body: ProductUpdate,
    current_user: User = Depends(PRODUCT_MANAGERS),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[ProductDetail]:
    data = await products_admin.update_product(db, code, body, current_user)
    return SuccessResponse(data=data)


@router.delete("/products/{code}", response_model=MessageResponse)
async def delete_product(
    code: int,
    current_user: User = Depends(PRODUCT_MANAGERS),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    await products_admin.delete_product(db, code, current_user)
    return MessageResponse(message="Продукт удален")


@router.get("/products/{code}", response_model=SuccessResponse[ProductDetail])
async def get_product(
    code: int,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[ProductDetail]:
    result = await db.execute(
        select(Product)
        .options(
            selectinload(Product.plant),
            selectinload(Product.modified_by_user),
        )
        .where(Product.code == code, Product.deleted_at.is_(None))
    )
    product = result.scalar_one_or_none()
    if product is None:
        raise APIError(404, "NOT_FOUND", "Продукт не найден")
    return SuccessResponse(data=to_product_detail(product))


@router.get("/objects", response_model=PaginatedResponse[list[ObjectListItem]])
async def list_objects(
    type: Literal["plant", "warehouse"] | None = Query(default=None),
    city: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[list[ObjectListItem]]:
    conditions = [Object.deleted_at.is_(None)]
    if type:
        conditions.append(Object.type == type)
    if city:
        conditions.append(Object.city.ilike(f"%{city.strip()}%"))
    if is_active is not None:
        conditions.append(Object.is_active == is_active)

    total = await db.scalar(select(func.count()).select_from(Object).where(*conditions))
    result = await db.execute(
        _paginate(
            select(Object).where(*conditions).order_by(Object.code),
            page,
            limit,
        )
    )
    objects = result.scalars().all()
    return PaginatedResponse(
        data=[ObjectListItem.model_validate(item) for item in objects],
        meta=PaginationMeta(page=page, limit=limit, total=total or 0),
    )


@router.get("/objects/{code}", response_model=SuccessResponse[ObjectListItem])
async def get_object(
    code: int,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[ObjectListItem]:
    result = await db.execute(
        select(Object).where(Object.code == code, Object.deleted_at.is_(None))
    )
    obj = result.scalar_one_or_none()
    if obj is None:
        raise APIError(404, "NOT_FOUND", "Объект не найден")
    return SuccessResponse(data=ObjectListItem.model_validate(obj))


@router.get("/users", response_model=SuccessResponse[list[UserReference]])
async def list_users(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[list[UserReference]]:
    if current_user.role == "guest":
        raise APIError(403, "FORBIDDEN", "Недостаточно прав")
    result = await db.execute(
        select(User).where(User.deleted_at.is_(None)).order_by(User.full_name)
    )
    users = result.scalars().all()
    return SuccessResponse(data=[UserReference.model_validate(user) for user in users])
