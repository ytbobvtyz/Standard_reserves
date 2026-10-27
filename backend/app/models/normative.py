import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CHAR,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin
from app.models.client import SYSTEM_CLIENT_ID

if TYPE_CHECKING:
    from app.models.client import Client
    from app.models.object import Object
    from app.models.product import Product
    from app.models.production_request import ProductionRequestItem
    from app.models.request import Request


class Normative(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "normatives"
    __table_args__ = (
        CheckConstraint("unit IN ('шт', 'кг', 'т')", name="ck_normatives_unit"),
        CheckConstraint("category IN ('A', 'B', 'C')", name="ck_normatives_category"),
        Index("idx_normatives_product_warehouse", "product_code", "warehouse_code"),
        Index("idx_normatives_product_code", "product_code"),
        Index("idx_normatives_warehouse_code", "warehouse_code"),
        Index("idx_normatives_expiry_date", "expiry_date"),
        Index(
            "idx_normatives_deleted_at",
            "deleted_at",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("idx_normatives_created_at", "created_at"),
        Index("idx_normatives_client_id", "client_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("requests.id"),
        nullable=True,
    )
    production_request_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("production_request_items.id", ondelete="CASCADE"),
        nullable=True,
        unique=True,
    )
    product_code: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("products.code"),
        nullable=False,
    )
    warehouse_code: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("objects.code"),
        nullable=False,
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(16, 6), nullable=False)
    unit: Mapped[str] = mapped_column(String(10), nullable=False)
    client_name: Mapped[str] = mapped_column(Text, nullable=False)
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="RESTRICT"),
        nullable=False,
        default=SYSTEM_CLIENT_ID,
        server_default=text("'00000000-0000-4000-8000-000000000001'"),
    )
    expiry_date: Mapped[date] = mapped_column(Date, nullable=False)
    category: Mapped[str] = mapped_column(CHAR(1), nullable=False)

    client: Mapped["Client"] = relationship("Client")
    request: Mapped["Request | None"] = relationship(
        "Request",
        back_populates="normatives",
    )
    production_request_item: Mapped["ProductionRequestItem | None"] = relationship(
        "ProductionRequestItem",
        back_populates="normative",
    )
    product: Mapped["Product"] = relationship("Product", back_populates="normatives")
    warehouse: Mapped["Object"] = relationship("Object", back_populates="normatives")
