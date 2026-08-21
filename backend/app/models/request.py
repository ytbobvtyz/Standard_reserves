import uuid
from calendar import monthrange
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin

MAX_EXPIRY_MONTHS = 6

if TYPE_CHECKING:
    from app.models.event import Event
    from app.models.normative import Normative
    from app.models.request_item import RequestItem
    from app.models.user import User


class Request(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "requests"
    __table_args__ = (
        CheckConstraint(
            "request_type IN ('normative', 'one_time')",
            name="ck_requests_request_type",
        ),
        CheckConstraint(
            "status IN ("
            "'draft', 'pp_approved', 'economy_check', 'pp_rework', "
            "'economy_rework', 'active', 'approved', 'rejected', "
            "'expired', 'executed')",
            name="ck_requests_status",
        ),
        CheckConstraint(
            "pp_action IS NULL OR pp_action IN ('approve', 'reject', 'edit')",
            name="ck_requests_pp_action",
        ),
        CheckConstraint(
            "economy_action IS NULL OR economy_action IN "
            "('approve', 'reject', 'edit')",
            name="ck_requests_economy_action",
        ),
        Index("idx_requests_status_type", "status", "request_type"),
        Index("idx_requests_initiator_id", "initiator_id"),
        Index("idx_requests_client_name", "client_name"),
        Index("idx_requests_created_at", "created_at"),
        Index(
            "idx_requests_expiry_date",
            "expiry_date",
            postgresql_where=text("expiry_date IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    request_type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="draft",
        server_default=text("'draft'"),
    )
    client_name: Mapped[str] = mapped_column(Text, nullable=False)
    initiator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    initiator_comment: Mapped[str | None] = mapped_column(Text)
    comment_pp: Mapped[str | None] = mapped_column(Text)
    comment_economy: Mapped[str | None] = mapped_column(Text)
    expiry_date: Mapped[date | None] = mapped_column(Date)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    executed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
    )
    order_number: Mapped[str | None] = mapped_column(Text)
    executed_comment: Mapped[str | None] = mapped_column(Text)
    pp_approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pp_approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
    )
    pp_action: Mapped[str | None] = mapped_column(String(20))
    economy_approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    economy_approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
    )
    economy_action: Mapped[str | None] = mapped_column(String(20))

    initiator: Mapped["User"] = relationship(
        "User",
        foreign_keys=[initiator_id],
        back_populates="initiated_requests",
    )
    pp_approver: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[pp_approved_by],
        back_populates="pp_approved_requests",
    )
    economy_approver: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[economy_approved_by],
        back_populates="economy_approved_requests",
    )
    executor: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[executed_by],
        back_populates="executed_requests",
    )
    items: Mapped[list["RequestItem"]] = relationship(
        "RequestItem",
        back_populates="request",
        cascade="all, delete-orphan",
    )
    normatives: Mapped[list["Normative"]] = relationship(
        "Normative",
        back_populates="request",
    )
    events: Mapped[list["Event"]] = relationship(
        "Event",
        back_populates="request",
    )

    @staticmethod
    def add_months(value: date, months: int) -> date:
        month_index = value.month - 1 + months
        year = value.year + month_index // 12
        month = month_index % 12 + 1
        day = min(value.day, monthrange(year, month)[1])
        return date(year, month, day)

    @staticmethod
    def _as_utc_date(created_at: datetime) -> date:
        if created_at.tzinfo is not None:
            return created_at.astimezone(UTC).date()
        return created_at.date()

    @classmethod
    def max_expiry_date(cls, created_at: datetime) -> date:
        return cls.add_months(cls._as_utc_date(created_at), MAX_EXPIRY_MONTHS)

    @staticmethod
    def validate_expiry_date(expiry_date: date, created_at: datetime) -> bool:
        return expiry_date <= Request.max_expiry_date(created_at)
