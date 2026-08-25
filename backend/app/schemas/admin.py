from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

UserRole = Literal["commercial", "pp", "economist", "logistics", "guest"]
EMAIL_RE = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class UserCreate(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=255, pattern=EMAIL_RE)
    full_name: str = Field(min_length=1, max_length=500)
    role: UserRole
    department_id: UUID | None = None
    password: str = Field(min_length=8, max_length=72)

    @field_validator("username", "full_name")
    @classmethod
    def strip_required(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("Поле не может быть пустым")
        return text

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class UserUpdate(BaseModel):
    email: str = Field(min_length=3, max_length=255, pattern=EMAIL_RE)
    full_name: str = Field(min_length=1, max_length=500)
    role: UserRole
    department_id: UUID | None = None
    is_active: bool = True

    @field_validator("full_name")
    @classmethod
    def strip_full_name(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("Поле не может быть пустым")
        return text

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: str
    full_name: str
    role: str
    department_id: UUID | None = None
    department_name: str | None = None
    is_active: bool
    created_at: datetime
    deleted_at: datetime | None = None


class PasswordResetResponse(BaseModel):
    new_password: str


class DepartmentOption(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    is_active: bool
