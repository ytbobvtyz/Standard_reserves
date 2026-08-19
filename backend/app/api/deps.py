from collections.abc import Callable, Coroutine
from typing import Any
from uuid import UUID

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import APIError
from app.core.security import decode_token
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None or not credentials.credentials:
        raise APIError(401, "UNAUTHORIZED", "Не авторизован")

    try:
        payload = decode_token(credentials.credentials)
    except jwt.ExpiredSignatureError as exc:
        raise APIError(401, "TOKEN_EXPIRED", "Срок действия токена истек") from exc
    except jwt.InvalidTokenError as exc:
        raise APIError(401, "INVALID_TOKEN", "Недействительный токен") from exc

    if payload.get("type") != "access":
        raise APIError(401, "INVALID_TOKEN", "Недействительный токен")

    subject = payload.get("sub")
    if not subject:
        raise APIError(401, "INVALID_TOKEN", "Недействительный токен")

    try:
        user_id = UUID(str(subject))
    except ValueError as exc:
        raise APIError(401, "INVALID_TOKEN", "Недействительный токен") from exc

    result = await db.execute(
        select(User).where(User.id == user_id, User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise APIError(401, "UNAUTHORIZED", "Не авторизован")
    if not user.is_active:
        raise APIError(403, "ACCOUNT_DISABLED", "Учетная запись заблокирована")
    return user


def require_roles(*roles: str) -> Callable[..., Coroutine[Any, Any, User]]:
    async def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise APIError(403, "FORBIDDEN", "Недостаточно прав")
        return current_user

    return checker


__all__ = [
    "bearer_scheme",
    "get_current_user",
    "get_db",
    "require_roles",
]
