import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.request_item import RequestItem
    from app.models.user import User


class RequestItemHistory(Base):
    __tablename__ = "request_item_history"
    __table_args__ = (
        CheckConstraint(
            "field_name IN ('quantity_requested', 'quantity_approved')",
            name="ck_request_item_history_field_name",
        ),
        Index("idx_request_item_history_item_id", "request_item_id"),
        Index("idx_request_item_history_changed_by", "changed_by"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    request_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("request_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    field_name: Mapped[str] = mapped_column(String(30), nullable=False)
    old_value: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    new_value: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    changed_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )
    comment: Mapped[str | None] = mapped_column(Text)

    request_item: Mapped["RequestItem"] = relationship(
        "RequestItem",
        back_populates="history",
    )
    changed_by_user: Mapped["User"] = relationship(
        "User",
        back_populates="item_changes",
    )
