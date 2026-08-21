from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.object import Object
    from app.models.product import Product


class AvailableBalance(Base):
    __tablename__ = "available_balances"
    __table_args__ = (
        CheckConstraint(
            "unit IN ('шт', 'т', 'ШТ', 'КГ')",
            name="ck_available_balances_unit",
        ),
        Index("idx_available_balances_warehouse", "warehouse_code"),
        Index("idx_available_balances_product", "product_code"),
        Index(
            "idx_available_balances_available",
            "available",
            postgresql_where=text("available > 0"),
        ),
    )

    warehouse_code: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("objects.code"),
        primary_key=True,
    )
    product_code: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("products.code"),
        primary_key=True,
    )
    available: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0"),
        server_default=text("0"),
    )
    plan: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0"),
        server_default=text("0"),
    )
    unit: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="шт",
        server_default=text("'шт'"),
    )
    last_sync_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
    source: Mapped[str | None] = mapped_column(
        String(50),
        default="manual",
        server_default=text("'manual'"),
    )

    warehouse: Mapped["Object"] = relationship(
        "Object",
        back_populates="available_balances",
    )
    product: Mapped["Product"] = relationship(
        "Product",
        back_populates="available_balances",
    )
