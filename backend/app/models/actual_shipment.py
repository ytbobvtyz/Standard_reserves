import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.client import Client
    from app.models.product import Product
    from app.models.user import User


class ActualShipment(TimestampMixin, SoftDeleteMixin, Base):
    """One line of actual client shipment loaded from Excel."""

    __tablename__ = "actual_shipments"
    __table_args__ = (
        CheckConstraint(
            "unit IN ('шт', 'кг', 'т')",
            name="ck_actual_shipments_unit",
        ),
        CheckConstraint(
            "quantity > 0",
            name="ck_actual_shipments_quantity",
        ),
        Index("idx_actual_shipments_client", "client_id"),
        Index("idx_actual_shipments_product", "product_code"),
        Index("idx_actual_shipments_date", "shipment_date"),
        Index("idx_actual_shipments_client_date", "client_id", "shipment_date"),
        Index("idx_actual_shipments_loading_point", "loading_point"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id"),
        nullable=False,
    )
    product_code: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("products.code"),
        nullable=False,
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    unit: Mapped[str] = mapped_column(String(10), nullable=False)
    shipment_date: Mapped[date] = mapped_column(Date, nullable=False)
    loading_point: Mapped[str] = mapped_column(String(10), nullable=False)
    invoice_number: Mapped[str | None] = mapped_column(String(25))
    route: Mapped[str | None] = mapped_column(String(50))
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )

    client: Mapped["Client"] = relationship("Client")
    product: Mapped["Product"] = relationship("Product")
    uploader: Mapped["User | None"] = relationship("User")
