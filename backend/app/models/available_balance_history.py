import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin


class AvailableBalanceHistory(CreatedAtMixin, Base):
    """Daily snapshot of ERP balances written by the Excel upload."""

    __tablename__ = "available_balances_history"
    __table_args__ = (
        CheckConstraint(
            "unit IN ('шт', 'кг', 'т', 'ШТ', 'КГ')",
            name="ck_available_balances_history_unit",
        ),
        Index(
            "uq_available_history_daily",
            "snapshot_date",
            "warehouse_code",
            "product_code",
            unique=True,
        ),
        Index("idx_available_history_date", "snapshot_date"),
        Index("idx_available_history_product", "product_code", "snapshot_date"),
        Index("idx_available_history_warehouse", "warehouse_code", "snapshot_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    snapshot_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    warehouse_code: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("objects.code"),
        nullable=False,
    )
    product_code: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("products.code"),
        nullable=False,
    )
    available: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    plan: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    full_stock: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0"),
        server_default=text("0"),
    )
    unit: Mapped[str] = mapped_column(String(10), nullable=False)
    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="excel_upload",
        server_default=text("'excel_upload'"),
    )
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )
