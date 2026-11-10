from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ActivityUser(BaseModel):
    id: UUID
    full_name: str
    role: str


class ActivityEvent(BaseModel):
    id: UUID
    created_at: datetime
    user: ActivityUser | None = None
    event_type: str
    entity_type: str | None = None
    entity_id: UUID | None = None
    entity_label: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
