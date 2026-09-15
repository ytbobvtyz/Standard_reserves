from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.params import Params
from app.models.user import User
from app.schemas.params import ParamsLastModifiedBy, ParamsResponse, ParamsUpdate
from app.services.coefficients import DEFAULT_COEFFICIENTS, CoefficientSet


def _defaults_row() -> Params:
    return Params(
        id=1,
        category_a=DEFAULT_COEFFICIENTS.category_a,
        category_b=DEFAULT_COEFFICIENTS.category_b,
        category_c=DEFAULT_COEFFICIENTS.category_c,
        remote_warehouse=DEFAULT_COEFFICIENTS.remote_warehouse,
        pallet_multiple=False,
    )


async def get_or_create_params(db: AsyncSession) -> Params:
    result = await db.execute(
        select(Params)
        .options(selectinload(Params.modified_by_user))
        .where(Params.id == 1)
    )
    row = result.scalar_one_or_none()
    if row is not None:
        return row
    row = _defaults_row()
    db.add(row)
    await db.flush()
    await db.refresh(row)
    return row


async def load_coefficient_set(db: AsyncSession) -> CoefficientSet:
    row = await db.get(Params, 1)
    if row is None:
        return DEFAULT_COEFFICIENTS
    return CoefficientSet(
        category_a=Decimal(row.category_a),
        category_b=Decimal(row.category_b),
        category_c=Decimal(row.category_c),
        remote_warehouse=Decimal(row.remote_warehouse),
    )


def to_response(row: Params) -> ParamsResponse:
    user = row.modified_by_user
    return ParamsResponse(
        category_a=row.category_a,
        category_b=row.category_b,
        category_c=row.category_c,
        remote_warehouse=row.remote_warehouse,
        pallet_multiple=bool(row.pallet_multiple),
        last_modified_by=(
            None if user is None else ParamsLastModifiedBy.model_validate(user)
        ),
        last_modified_at=row.last_modified_at,
    )


async def get_params(db: AsyncSession) -> ParamsResponse:
    result = await db.execute(
        select(Params)
        .options(selectinload(Params.modified_by_user))
        .where(Params.id == 1)
    )
    row = result.scalar_one_or_none()
    if row is None:
        row = await get_or_create_params(db)
        await db.commit()
        result = await db.execute(
            select(Params)
            .options(selectinload(Params.modified_by_user))
            .where(Params.id == 1)
        )
        row = result.scalar_one()
    return to_response(row)


async def update_params(
    db: AsyncSession, body: ParamsUpdate, user_id: UUID
) -> ParamsResponse:
    row = await get_or_create_params(db)
    row.category_a = body.category_a
    row.category_b = body.category_b
    row.category_c = body.category_c
    row.remote_warehouse = body.remote_warehouse
    row.pallet_multiple = body.pallet_multiple
    row.last_modified_by = user_id
    row.last_modified_at = datetime.now(UTC)
    row.updated_at = datetime.now(UTC)
    await db.commit()
    user = await db.get(User, user_id)
    return ParamsResponse(
        category_a=row.category_a,
        category_b=row.category_b,
        category_c=row.category_c,
        remote_warehouse=row.remote_warehouse,
        pallet_multiple=bool(row.pallet_multiple),
        last_modified_by=(
            None if user is None else ParamsLastModifiedBy.model_validate(user)
        ),
        last_modified_at=row.last_modified_at,
    )
