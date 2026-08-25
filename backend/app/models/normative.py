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

if TYPE_CHECKING:
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
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    unit: Mapped[str] = mapped_column(String(10), nullable=False)
    client_name: Mapped[str] = mapped_column(Text, nullable=False)
    expiry_date: Mapped[date] = mapped_column(Date, nullable=False)
    category: Mapped[str] = mapped_column(CHAR(1), nullable=False)

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
