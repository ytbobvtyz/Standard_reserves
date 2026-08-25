from __future__ import annotations

import secrets
import string
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import APIError
from app.core.pagination import paginate
from app.core.security import hash_password
from app.models.department import Department
from app.models.session import Session
from app.models.user import User
from app.schemas.admin import (
    DepartmentOption,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from app.services.audit import add_audit_log

PASSWORD_ALPHABET = string.ascii_letters + string.digits
PASSWORD_LENGTH = 8


def generate_password(length: int = PASSWORD_LENGTH) -> str:
    return "".join(secrets.choice(PASSWORD_ALPHABET) for _ in range(length))


def to_user_response(user: User) -> UserResponse:
    department = user.assigned_department
    department_name = department.name if department else user.department
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        department_id=user.department_id,
        department_name=department_name,
        is_active=user.is_active,
        created_at=user.created_at,
        deleted_at=user.deleted_at,
    )


async def _load_user(
    db: AsyncSession,
    user_id: UUID,
    *,
    include_deleted: bool = False,
) -> User | None:
    stmt = (
        select(User)
        .options(selectinload(User.assigned_department))
        .where(User.id == user_id)
        .execution_options(populate_existing=True)
    )
    if not include_deleted:
        stmt = stmt.where(User.deleted_at.is_(None))
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def _require_user(
    db: AsyncSession,
    user_id: UUID,
    *,
    include_deleted: bool = False,
) -> User:
    user = await _load_user(db, user_id, include_deleted=include_deleted)
    if user is None:
        raise APIError(404, "NOT_FOUND", "Пользователь не найден")
    return user


async def _resolve_department(
    db: AsyncSession, department_id: UUID | None
) -> Department | None:
    if department_id is None:
        return None
    department = await db.scalar(
        select(Department).where(
            Department.id == department_id,
            Department.deleted_at.is_(None),
        )
    )
    if department is None:
        raise APIError(400, "VALIDATION_ERROR", "Подразделение не найдено")
    return department


async def _username_taken(
    db: AsyncSession, username: str, *, exclude_id: UUID | None = None
) -> bool:
    stmt = select(User.id).where(User.username == username)
    if exclude_id is not None:
        stmt = stmt.where(User.id != exclude_id)
    return await db.scalar(stmt) is not None


async def _email_taken(
    db: AsyncSession, email: str, *, exclude_id: UUID | None = None
) -> bool:
    stmt = select(User.id).where(func.lower(User.email) == email.lower())
    if exclude_id is not None:
        stmt = stmt.where(User.id != exclude_id)
    return await db.scalar(stmt) is not None


async def _active_logistics_count(
    db: AsyncSession, *, exclude_id: UUID | None = None
) -> int:
    conditions = [
        User.role == "logistics",
        User.deleted_at.is_(None),
        User.is_active.is_(True),
    ]
    if exclude_id is not None:
        conditions.append(User.id != exclude_id)
    count = await db.scalar(select(func.count()).select_from(User).where(*conditions))
    return int(count or 0)


def _ensure_not_last_logistics(remaining: int) -> None:
    if remaining <= 0:
        raise APIError(
            400,
            "LAST_LOGISTICS",
            "Нельзя удалить или изменить роль последнего логиста",
        )


async def _revoke_sessions(db: AsyncSession, user_id: UUID) -> None:
    await db.execute(
        update(Session)
        .where(Session.user_id == user_id, Session.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )


async def list_users(
    db: AsyncSession,
    *,
    search: str | None,
    role: str | None,
    department_id: UUID | None,
    is_active: bool | None,
    deleted: bool | None,
    page: int,
    limit: int,
) -> tuple[list[UserResponse], int]:
    conditions = []
    if deleted:
        conditions.append(User.deleted_at.is_not(None))
    else:
        conditions.append(User.deleted_at.is_(None))
    if search:
        term = f"%{search.strip()}%"
        conditions.append(
            or_(
                User.username.ilike(term),
                User.email.ilike(term),
                User.full_name.ilike(term),
            )
        )
    if role:
        conditions.append(User.role == role)
    if department_id is not None:
        conditions.append(User.department_id == department_id)
    if is_active is not None:
        conditions.append(User.is_active == is_active)

    total = await db.scalar(select(func.count()).select_from(User).where(*conditions))
    result = await db.execute(
        paginate(
            select(User)
            .options(selectinload(User.assigned_department))
            .where(*conditions)
            .order_by(User.full_name, User.username),
            page,
            limit,
        )
    )
    users = list(result.scalars().all())
    return [to_user_response(user) for user in users], int(total or 0)


async def get_user(db: AsyncSession, user_id: UUID) -> UserResponse:
    user = await _require_user(db, user_id, include_deleted=True)
    return to_user_response(user)


async def create_user(db: AsyncSession, data: UserCreate, actor: User) -> UserResponse:
    if await _username_taken(db, data.username):
        raise APIError(
            409, "ALREADY_EXISTS", "Пользователь с таким логином уже существует"
        )
    if await _email_taken(db, data.email):
        raise APIError(
            409, "ALREADY_EXISTS", "Пользователь с таким email уже существует"
        )

    department = await _resolve_department(db, data.department_id)
    user = User(
        username=data.username,
        email=data.email,
        password_hash=hash_password(data.password),
        full_name=data.full_name,
        role=data.role,
        department=department.name if department else None,
        department_id=department.id if department else None,
        is_active=True,
    )
    db.add(user)
    add_audit_log(
        db,
        entity_type="user",
        entity_id=data.username,
        action="create",
        user=actor,
        payload={"username": data.username, "role": data.role},
    )
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise APIError(
            409,
            "ALREADY_EXISTS",
            "Пользователь с таким логином или email уже существует",
        ) from exc
    created = await _require_user(db, user.id)
    return to_user_response(created)


async def update_user(
    db: AsyncSession, user_id: UUID, data: UserUpdate, actor: User
) -> UserResponse:
    user = await _require_user(db, user_id)
    if await _email_taken(db, data.email, exclude_id=user.id):
        raise APIError(
            409, "ALREADY_EXISTS", "Пользователь с таким email уже существует"
        )

    losing_logistics = (
        user.role == "logistics"
        and user.is_active
        and (data.role != "logistics" or not data.is_active)
    )
    if losing_logistics:
        remaining = await _active_logistics_count(db, exclude_id=user.id)
        _ensure_not_last_logistics(remaining)

    department = await _resolve_department(db, data.department_id)
    before = {
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "department_id": str(user.department_id) if user.department_id else None,
        "is_active": user.is_active,
    }
    user.email = data.email
    user.full_name = data.full_name
    user.role = data.role
    user.department_id = department.id if department else None
    user.department = department.name if department else None
    user.is_active = data.is_active
    if not data.is_active:
        await _revoke_sessions(db, user.id)
    add_audit_log(
        db,
        entity_type="user",
        entity_id=str(user.id),
        action="update",
        user=actor,
        payload={"before": before},
    )
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise APIError(
            409, "ALREADY_EXISTS", "Пользователь с таким email уже существует"
        ) from exc
    updated = await _require_user(db, user_id)
    return to_user_response(updated)


async def delete_user(db: AsyncSession, user_id: UUID, current_user: User) -> None:
    user = await _require_user(db, user_id)
    if user.id == current_user.id:
        raise APIError(
            400, "CANNOT_DELETE_SELF", "Нельзя удалить собственную учётную запись"
        )
    if user.role == "logistics" and user.is_active:
        remaining = await _active_logistics_count(db, exclude_id=user.id)
        _ensure_not_last_logistics(remaining)

    user.deleted_at = datetime.now(UTC)
    await _revoke_sessions(db, user.id)
    add_audit_log(
        db,
        entity_type="user",
        entity_id=str(user.id),
        action="delete",
        user=current_user,
        payload={"username": user.username, "role": user.role},
    )
    await db.commit()


async def reset_password(db: AsyncSession, user_id: UUID, actor: User) -> str:
    user = await _require_user(db, user_id)
    new_password = generate_password()
    user.password_hash = hash_password(new_password)
    await _revoke_sessions(db, user.id)
    add_audit_log(
        db,
        entity_type="user",
        entity_id=str(user.id),
        action="update",
        user=actor,
        payload={"action": "reset_password", "username": user.username},
    )
    await db.commit()
    return new_password


async def list_departments(db: AsyncSession) -> list[DepartmentOption]:
    result = await db.execute(
        select(Department)
        .where(Department.deleted_at.is_(None), Department.is_active.is_(True))
        .order_by(Department.name)
    )
    return [DepartmentOption.model_validate(item) for item in result.scalars().all()]


__all__ = [
    "create_user",
    "delete_user",
    "generate_password",
    "get_user",
    "list_departments",
    "list_users",
    "reset_password",
    "to_user_response",
    "update_user",
]
