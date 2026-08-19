import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin

if TYPE_CHECKING:
    from app.models.request import Request


class Event(CreatedAtMixin, Base):
    __tablename__ = "events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ("
            "'request_created', 'request_approved', 'request_rejected', "
            "'normative_active', 'normative_expired', "
            "'deficit_detected', 'deficit_resolved')",
            name="ck_events_event_type",
        ),
        Index(
            "idx_events_processed",
            "processed",
            postgresql_where=text("processed = false"),
        ),
        Index("idx_events_request_id", "request_id"),
        Index("idx_events_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("requests.id"),
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    processed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    request: Mapped["Request | None"] = relationship("Request", back_populates="events")
