from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.security import require_strong_password


class UserBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    full_name: str
    role: str
    department: str | None = None
    department_id: UUID | None = None


class UserProfile(UserBrief):
    email: str
    last_login_at: datetime | None = None


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=72)

    @field_validator("new_password")
    @classmethod
    def check_new_password(cls, value: str) -> str:
        return require_strong_password(value)
