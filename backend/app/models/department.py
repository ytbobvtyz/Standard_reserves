import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Index, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.request import Request
    from app.models.user import User


class Department(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "departments"
    __table_args__ = (
        Index(
            "uq_departments_name",
            "name",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "idx_departments_is_active",
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
    name: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    users: Mapped[list["User"]] = relationship(
        "User",
        back_populates="assigned_department",
        foreign_keys="User.department_id",
    )
    requests: Mapped[list["Request"]] = relationship(
        "Request",
        back_populates="department",
        foreign_keys="Request.department_id",
    )
