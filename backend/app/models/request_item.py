import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.object import Object
    from app.models.product import Product
    from app.models.request import Request
    from app.models.request_item_history import RequestItemHistory


class RequestItem(TimestampMixin, Base):
    __tablename__ = "request_items"
    __table_args__ = (
        CheckConstraint("quantity_requested > 0", name="ck_request_items_qty_req"),
        CheckConstraint("unit IN ('шт', 'т')", name="ck_request_items_unit"),
        UniqueConstraint(
            "request_id",
            "product_code",
            "warehouse_code",
            name="uq_request_items_request_product_warehouse",
        ),
        Index("idx_request_items_request_id", "request_id"),
        Index("idx_request_items_product_code", "product_code"),
        Index("idx_request_items_warehouse_code", "warehouse_code"),
        Index(
            "idx_request_items_product_warehouse",
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
    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("requests.id", ondelete="CASCADE"),
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
    quantity_requested: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    quantity_approved: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    unit: Mapped[str] = mapped_column(String(10), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)

    request: Mapped["Request"] = relationship("Request", back_populates="items")
    product: Mapped["Product"] = relationship(
        "Product",
        back_populates="request_items",
    )
    warehouse: Mapped["Object"] = relationship(
        "Object",
        back_populates="request_items",
    )
    history: Mapped[list["RequestItemHistory"]] = relationship(
        "RequestItemHistory",
        back_populates="request_item",
        cascade="all, delete-orphan",
    )
