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
    from app.models.user import User

EVENT_TYPES = (
    "request_created",
    "request_submitted",
    "request_approved",
    "request_rejected",
    "request_deleted",
    "request_expiry_changed",
    "normative_active",
    "normative_expired",
    "deficit_detected",
    "deficit_resolved",
    "normative_replaced_by_name",
    "user_logged_in",
    "user_registered",
    "user_updated",
    "user_deleted",
    "password_changed",
    "product_created",
    "product_updated",
    "product_deleted",
    "client_created",
    "client_updated",
    "client_deleted",
    "object_created",
    "object_updated",
    "object_deleted",
    "balances_uploaded",
    "actual_shipments_uploaded",
    "production_request_uploaded",
    "export_generated",
)

_EVENT_TYPE_SQL = (
    "event_type IN (" + ", ".join(f"'{item}'" for item in EVENT_TYPES) + ")"
)


class Event(CreatedAtMixin, Base):
    __tablename__ = "events"
    __table_args__ = (
        CheckConstraint(_EVENT_TYPE_SQL, name="ck_events_event_type"),
        Index(
            "idx_events_processed",
            "processed",
            postgresql_where=text("processed = false"),
        ),
        Index("idx_events_request_id", "request_id"),
        Index("idx_events_created_at", "created_at"),
        Index("idx_events_user_id", "user_id"),
        Index("idx_events_entity", "entity_type", "entity_id"),
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
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    entity_type: Mapped[str | None] = mapped_column(String(50))
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    details: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    request: Mapped["Request | None"] = relationship("Request", back_populates="events")
    actor: Mapped["User | None"] = relationship("User")
