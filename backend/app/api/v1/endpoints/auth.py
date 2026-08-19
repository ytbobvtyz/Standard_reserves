import ipaddress
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import APIRouter, Depends, Request
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.core.exceptions import APIError
from app.core.security import (
    access_token_expires_in,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.session import Session
from app.models.user import User
from app.schemas.auth import (
    AccessTokenData,
    LoginRequest,
    RefreshRequest,
    TokenPairData,
)
from app.schemas.common import MessageResponse, SuccessResponse
from app.schemas.user import ChangePasswordRequest, UserBrief, UserProfile

router = APIRouter(prefix="/auth", tags=["Аутентификация"])


def _client_ip(request: Request) -> str | None:
    host = request.client.host if request.client else None
    if not host:
        return None
    try:
        ipaddress.ip_address(host)
        return host
    except ValueError:
        return None


def _user_payload(user: User) -> dict[str, str]:
    return {"sub": str(user.id), "username": user.username, "role": user.role}


async def _get_user_by_username(db: AsyncSession, username: str) -> User | None:
    result = await db.execute(
        select(User).where(User.username == username, User.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


@router.post("/login", response_model=SuccessResponse[TokenPairData])
async def login(
    body: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[TokenPairData]:
    user = await _get_user_by_username(db, body.username)
    if user is None or not verify_password(body.password, user.password_hash):
        raise APIError(401, "INVALID_CREDENTIALS", "Неверный логин или пароль")
    if not user.is_active:
        raise APIError(403, "ACCOUNT_DISABLED", "Учетная запись заблокирована")

    now = datetime.now(UTC)
    access_token = create_access_token(_user_payload(user))
    refresh_token = create_refresh_token({"sub": str(user.id)})

    user.last_login_at = now
    db.add(
        Session(
            user_id=user.id,
            token=refresh_token,
            ip_address=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
            expires_at=now + timedelta(days=settings.refresh_token_expire_days),
        )
    )
    await db.commit()
    await db.refresh(user)

    return SuccessResponse(
        data=TokenPairData(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=access_token_expires_in(),
            user=UserBrief.model_validate(user),
        )
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    await db.execute(
        update(Session)
        .where(Session.user_id == current_user.id, Session.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )
    await db.commit()
    return MessageResponse(message="Вы вышли из системы")


@router.post("/refresh", response_model=SuccessResponse[AccessTokenData])
async def refresh(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[AccessTokenData]:
    try:
        payload = decode_token(body.refresh_token)
    except jwt.ExpiredSignatureError as exc:
        raise APIError(401, "TOKEN_EXPIRED", "Срок действия токена истек") from exc
    except jwt.InvalidTokenError as exc:
        raise APIError(401, "INVALID_TOKEN", "Недействительный токен") from exc

    if payload.get("type") != "refresh":
        raise APIError(401, "INVALID_TOKEN", "Недействительный токен")

    result = await db.execute(
        select(Session).where(
            Session.token == body.refresh_token,
            Session.revoked_at.is_(None),
        )
    )
    session = result.scalar_one_or_none()
    now = datetime.now(UTC)
    if session is None or session.expires_at < now:
        raise APIError(401, "INVALID_TOKEN", "Недействительный токен")

    user_result = await db.execute(
        select(User).where(User.id == session.user_id, User.deleted_at.is_(None))
    )
    user = user_result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise APIError(401, "UNAUTHORIZED", "Не авторизован")

    access_token = create_access_token(_user_payload(user))
    return SuccessResponse(
        data=AccessTokenData(
            access_token=access_token,
            expires_in=access_token_expires_in(),
        )
    )


@router.get("/profile", response_model=SuccessResponse[UserProfile])
async def profile(
    current_user: User = Depends(get_current_user),
) -> SuccessResponse[UserProfile]:
    return SuccessResponse(data=UserProfile.model_validate(current_user))


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    if not verify_password(body.old_password, current_user.password_hash):
        raise APIError(400, "INVALID_PASSWORD", "Неверный текущий пароль")
    if body.old_password == body.new_password:
        raise APIError(
            400, "PASSWORD_UNCHANGED", "Новый пароль должен отличаться от текущего"
        )

    current_user.password_hash = hash_password(body.new_password)
    await db.execute(
        update(Session)
        .where(Session.user_id == current_user.id, Session.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )
    await db.commit()
    return MessageResponse(message="Пароль изменен")
