from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import exists, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import APIError
from app.models.audit_log import AuditLog
from app.models.available_balance import AvailableBalance
from app.models.normative import Normative
from app.models.object import Object
from app.models.product import Product
from app.models.request_item import RequestItem
from app.models.user import User
from app.schemas.reference import ObjectCreate, ObjectDetail, ObjectUpdate
from app.services.references import to_object_detail

OBJECT_TYPES = {"plant", "warehouse"}


async def _load_object(db: AsyncSession, code: int) -> Object | None:
    result = await db.execute(
        select(Object)
        .options(selectinload(Object.modified_by_user))
        .where(Object.code == code, Object.deleted_at.is_(None))
        .execution_options(populate_existing=True)
    )
    return result.scalar_one_or_none()


def _touch(obj: Object, user: User) -> None:
    obj.last_modified_by = user.id
    obj.last_modified_at = datetime.now(UTC)


def _audit(
    db: AsyncSession,
    *,
    user: User,
    action: str,
    entity_id: str,
    payload: dict[str, Any],
) -> None:
    db.add(
        AuditLog(
            entity_type="object",
            entity_id=entity_id,
            action=action,
            changed_by=user.id,
            payload=payload,
        )
    )


async def get_object_for_edit(db: AsyncSession, code: int) -> ObjectDetail:
    obj = await _load_object(db, code)
    if obj is None:
        raise APIError(404, "NOT_FOUND", "Объект не найден")
    return to_object_detail(obj)


async def create_object(
    db: AsyncSession, body: ObjectCreate, user: User
) -> ObjectDetail:
    existing = await db.scalar(select(Object.code).where(Object.code == body.code))
    if existing is not None:
        raise APIError(
            409,
            "ALREADY_EXISTS",
            f"Объект с кодом {body.code} уже существует",
        )
    if body.type not in OBJECT_TYPES:
        raise APIError(400, "VALIDATION_ERROR", "type должен быть plant или warehouse")

    obj = Object(
        code=body.code,
        name=body.name,
        city=body.city,
        region=body.region,
        address=body.address,
        type=body.type,
        is_active=body.is_active,
    )
    _touch(obj, user)
    db.add(obj)
    _audit(
        db,
        user=user,
        action="create",
        entity_id=str(body.code),
        payload={"name": body.name, "type": body.type},
    )
    await db.commit()
    created = await _load_object(db, body.code)
    assert created is not None
    return to_object_detail(created)


async def update_object(
    db: AsyncSession, code: int, body: ObjectUpdate, user: User
) -> ObjectDetail:
    obj = await _load_object(db, code)
    if obj is None:
        raise APIError(404, "NOT_FOUND", "Объект не найден")

    updates = body.model_dump(exclude_unset=True)
    if "type" in updates and updates["type"] not in OBJECT_TYPES:
        raise APIError(400, "VALIDATION_ERROR", "type должен быть plant или warehouse")

    before = {
        "name": obj.name,
        "city": obj.city,
        "type": obj.type,
        "is_active": obj.is_active,
    }
    for field, value in updates.items():
        setattr(obj, field, value)
    _touch(obj, user)
    _audit(
        db,
        user=user,
        action="update",
        entity_id=str(code),
        payload={"before": before},
    )
    await db.commit()
    db.expire_all()
    updated = await _load_object(db, code)
    assert updated is not None
    return to_object_detail(updated)


async def delete_object(db: AsyncSession, code: int, user: User) -> None:
    obj = await _load_object(db, code)
    if obj is None:
        raise APIError(404, "NOT_FOUND", "Объект не найден")

    has_products = await db.scalar(
        select(
            exists().where(
                Product.deleted_at.is_(None),
                or_(
                    Product.plant_id == code,
                    Product.second_plant_id == code,
                    Product.third_plant_id == code,
                ),
            )
        )
    )
    has_items = await db.scalar(
        select(exists().where(RequestItem.warehouse_code == code))
    )
    has_normatives = await db.scalar(
        select(
            exists().where(
                Normative.warehouse_code == code,
                Normative.deleted_at.is_(None),
            )
        )
    )
    has_balances = await db.scalar(
        select(exists().where(AvailableBalance.warehouse_code == code))
    )
    if has_products or has_items or has_normatives or has_balances:
        raise APIError(
            409,
            "HAS_RELATIONS",
            "Нельзя удалить объект: есть связанные продукты, "
            "позиции запросов, нормативы или остатки",
        )

    obj.deleted_at = datetime.now(UTC)
    _touch(obj, user)
    _audit(
        db,
        user=user,
        action="delete",
        entity_id=str(code),
        payload={"name": obj.name, "type": obj.type},
    )
    await db.commit()
