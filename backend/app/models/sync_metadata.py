from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class SyncMetadata(Base):
    """Singleton row (id = 1) with last balances upload metadata."""

    __tablename__ = "sync_metadata"
    __table_args__ = (
        CheckConstraint("id = 1", name="ck_sync_metadata_singleton"),
        Index("idx_sync_metadata_last_balances_sync_by", "last_balances_sync_by"),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        default=1,
        server_default=text("1"),
    )
    last_balances_sync_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_balances_sync_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    synced_by_user: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[last_balances_sync_by],
    )
