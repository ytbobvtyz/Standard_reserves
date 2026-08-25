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
    from app.models.normative import Normative
    from app.models.object import Object
    from app.models.product import Product
    from app.models.user import User


class ProductionRequest(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "production_requests"
    __table_args__ = (
        CheckConstraint(
            "source IN ('excel_upload')",
            name="ck_production_requests_source",
        ),
        CheckConstraint(
            "status IN ('active', 'archived', 'cancelled')",
            name="ck_production_requests_status",
        ),
        CheckConstraint(
            "valid_to >= valid_from",
            name="ck_production_requests_dates",
        ),
        Index("uq_production_requests_batch_id", "batch_id", unique=True),
        Index("idx_production_requests_uploaded_by", "uploaded_by"),
        Index("idx_production_requests_status", "status"),
        Index(
            "idx_production_requests_deleted_at",
            "deleted_at",
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="excel_upload",
        server_default=text("'excel_upload'"),
    )
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    client_name: Mapped[str | None] = mapped_column(Text)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="active",
        server_default=text("'active'"),
    )

    uploader: Mapped["User"] = relationship(
        "User",
        back_populates="production_requests",
        foreign_keys=[uploaded_by],
    )
    items: Mapped[list["ProductionRequestItem"]] = relationship(
        "ProductionRequestItem",
        back_populates="production_request",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ProductionRequestItem(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "production_request_items"
    __table_args__ = (
        CheckConstraint(
            "unit IN ('шт', 'кг', 'т')",
            name="ck_production_request_items_unit",
        ),
        CheckConstraint(
            "category IN ('A', 'B', 'C')",
            name="ck_production_request_items_category",
        ),
        CheckConstraint(
            "quantity > 0",
            name="ck_production_request_items_quantity",
        ),
        Index(
            "idx_production_request_items_request",
            "production_request_id",
        ),
        Index(
            "idx_production_request_items_product_warehouse",
            "product_code",
            "warehouse_code",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    production_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("production_requests.id", ondelete="CASCADE"),
        nullable=False,
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
    category: Mapped[str] = mapped_column(CHAR(1), nullable=False)

    production_request: Mapped["ProductionRequest"] = relationship(
        "ProductionRequest",
        back_populates="items",
    )
    product: Mapped["Product"] = relationship("Product")
    warehouse: Mapped["Object"] = relationship("Object")
    normative: Mapped["Normative | None"] = relationship(
        "Normative",
        back_populates="production_request_item",
        passive_deletes=True,
        uselist=False,
    )
