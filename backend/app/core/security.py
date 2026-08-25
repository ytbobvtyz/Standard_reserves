import re
import secrets
import string
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from passlib.context import CryptContext

from app.core.config import settings

ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

PASSWORD_MIN_LENGTH = 8
PASSWORD_SPECIAL_CHARS = "!@#$%^&*()_+-="
PASSWORD_SPECIAL_PATTERN = re.compile(r'[!@#$%^&*()_+\-=\[\]{};:"\\|,.<>/?]')
PASSWORD_REQUIREMENTS_MESSAGE = (
    "Пароль должен содержать минимум 8 символов, заглавную и строчную буквы, "
    "цифру и специальный символ"
)


def validate_password_strength(password: str) -> bool:
    if len(password) < PASSWORD_MIN_LENGTH:
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"[a-z]", password):
        return False
    if not re.search(r"[0-9]", password):
        return False
    if not PASSWORD_SPECIAL_PATTERN.search(password):
        return False
    return True


def require_strong_password(password: str) -> str:
    if not validate_password_strength(password):
        raise ValueError(PASSWORD_REQUIREMENTS_MESSAGE)
    return password


def generate_secure_password(length: int = PASSWORD_MIN_LENGTH) -> str:
    size = max(length, PASSWORD_MIN_LENGTH)
    required = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice(PASSWORD_SPECIAL_CHARS),
    ]
    alphabet = string.ascii_letters + string.digits + PASSWORD_SPECIAL_CHARS
    chars = required + [secrets.choice(alphabet) for _ in range(size - len(required))]
    secrets.SystemRandom().shuffle(chars)
    return "".join(chars)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return pwd_context.verify(password, password_hash)
    except (ValueError, TypeError):
        return False


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    expire = datetime.now(UTC) + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload = {
        **data,
        "type": "access",
        "exp": expire,
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def create_refresh_token(data: dict[str, Any]) -> str:
    expire = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
    payload = {
        **data,
        "type": "refresh",
        "jti": str(uuid.uuid4()),
        "exp": expire,
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])


def access_token_expires_in() -> int:
    return settings.access_token_expire_minutes * 60
