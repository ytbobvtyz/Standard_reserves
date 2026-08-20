import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.password_reset import PasswordResetToken
    from app.models.request import Request
    from app.models.request_item_history import RequestItemHistory
    from app.models.session import Session


class User(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "role IN ('commercial', 'pp', 'economist', 'logistics', 'guest')",
            name="ck_users_role",
        ),
        Index("idx_users_username", "username"),
        Index("idx_users_email", "email"),
        Index("idx_users_role", "role"),
        Index(
            "idx_users_is_active",
            "is_active",
            postgresql_where=text("is_active = true"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    username: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String(30), nullable=False)
    department: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    sessions: Mapped[list["Session"]] = relationship(
        "Session",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    password_reset_tokens: Mapped[list["PasswordResetToken"]] = relationship(
        "PasswordResetToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    initiated_requests: Mapped[list["Request"]] = relationship(
        "Request",
        back_populates="initiator",
        foreign_keys="Request.initiator_id",
    )
    pp_approved_requests: Mapped[list["Request"]] = relationship(
        "Request",
        back_populates="pp_approver",
        foreign_keys="Request.pp_approved_by",
    )
    economy_approved_requests: Mapped[list["Request"]] = relationship(
        "Request",
        back_populates="economy_approver",
        foreign_keys="Request.economy_approved_by",
    )
    executed_requests: Mapped[list["Request"]] = relationship(
        "Request",
        back_populates="executor",
        foreign_keys="Request.executed_by",
    )
    item_changes: Mapped[list["RequestItemHistory"]] = relationship(
        "RequestItemHistory",
        back_populates="changed_by_user",
    )
