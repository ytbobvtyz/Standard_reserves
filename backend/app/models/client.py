import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.department import Department

SYSTEM_CLIENT_ID = uuid.UUID("00000000-0000-4000-8000-000000000001")
SYSTEM_CLIENT_CODE = 9999999999
SYSTEM_CLIENT_INN = "0000000000"
SYSTEM_CLIENT_NAME = "Общий клиент"


class Client(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "clients"
    __table_args__ = (
        CheckConstraint(
            "client_code >= 1 AND client_code <= 9999999999",
            name="ck_clients_client_code",
        ),
        Index(
            "uq_clients_client_code",
            "client_code",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "idx_clients_inn",
            "inn",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("idx_clients_department_id", "department_id"),
        Index(
            "idx_clients_is_active",
            "is_active",
            postgresql_where=text("is_active = true"),
        ),
        Index(
            "idx_clients_name_trgm",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    client_code: Mapped[int] = mapped_column(BigInteger, nullable=False)
    inn: Mapped[str] = mapped_column(String(12), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    kpp: Mapped[str | None] = mapped_column(String(9))
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("departments.id", ondelete="RESTRICT"),
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    is_system: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )

    department: Mapped["Department | None"] = relationship("Department")
