from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class Params(Base):
    """Singleton row (id = 1) with global coefficient and request settings."""

    __tablename__ = "params"
    __table_args__ = (
        CheckConstraint("id = 1", name="ck_params_singleton"),
        CheckConstraint(
            "category_a >= 1 AND category_a <= 3",
            name="ck_params_category_a_range",
        ),
        CheckConstraint(
            "category_b >= 1 AND category_b <= 3",
            name="ck_params_category_b_range",
        ),
        CheckConstraint(
            "category_c >= 1 AND category_c <= 3",
            name="ck_params_category_c_range",
        ),
        CheckConstraint(
            "remote_warehouse >= 1 AND remote_warehouse <= 3",
            name="ck_params_remote_warehouse_range",
        ),
        Index("idx_params_last_modified_by", "last_modified_by"),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        default=1,
        server_default=text("1"),
    )
    category_a: Mapped[Decimal] = mapped_column(
        Numeric(3, 1),
        nullable=False,
        server_default=text("1.0"),
    )
    category_b: Mapped[Decimal] = mapped_column(
        Numeric(3, 1),
        nullable=False,
        server_default=text("1.5"),
    )
    category_c: Mapped[Decimal] = mapped_column(
        Numeric(3, 1),
        nullable=False,
        server_default=text("2.0"),
    )
    remote_warehouse: Mapped[Decimal] = mapped_column(
        Numeric(3, 1),
        nullable=False,
        server_default=text("1.5"),
    )
    pallet_multiple: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    last_modified_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    last_modified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    modified_by_user: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[last_modified_by],
    )
