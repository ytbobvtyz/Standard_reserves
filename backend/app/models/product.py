from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CHAR,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.available_balance import AvailableBalance
    from app.models.normative import Normative
    from app.models.object import Object
    from app.models.request_item import RequestItem


class Product(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("category IN ('A', 'B', 'C')", name="ck_products_category"),
        Index("idx_products_category", "category"),
        Index("idx_products_plant_id", "plant_id"),
        Index(
            "idx_products_is_active",
            "is_active",
            postgresql_where=text("is_active = true"),
        ),
        Index(
            "idx_products_parent_code",
            "parent_code",
            postgresql_where=text("parent_code IS NOT NULL"),
        ),
        Index(
            "idx_products_children_code",
            "children_code",
            postgresql_where=text("children_code IS NOT NULL"),
        ),
    )

    code: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str] = mapped_column(CHAR(1), nullable=False)
    plant_id: Mapped[int] = mapped_column(
        ForeignKey("objects.code"),
        nullable=False,
    )
    second_plant_id: Mapped[int | None] = mapped_column(ForeignKey("objects.code"))
    third_plant_id: Mapped[int | None] = mapped_column(ForeignKey("objects.code"))
    weight_kg: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    monthly_consumption: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    parent_code: Mapped[int | None] = mapped_column(ForeignKey("products.code"))
    children_code: Mapped[int | None] = mapped_column(ForeignKey("products.code"))

    plant: Mapped["Object"] = relationship(
        "Object",
        foreign_keys=[plant_id],
        back_populates="products_as_plant",
    )
    second_plant: Mapped["Object | None"] = relationship(
        "Object",
        foreign_keys=[second_plant_id],
    )
    third_plant: Mapped["Object | None"] = relationship(
        "Object",
        foreign_keys=[third_plant_id],
    )
    parent: Mapped["Product | None"] = relationship(
        "Product",
        foreign_keys=[parent_code],
        remote_side=[code],
    )
    child: Mapped["Product | None"] = relationship(
        "Product",
        foreign_keys=[children_code],
        remote_side=[code],
    )
    request_items: Mapped[list["RequestItem"]] = relationship(
        "RequestItem",
        back_populates="product",
    )
    normatives: Mapped[list["Normative"]] = relationship(
        "Normative",
        back_populates="product",
    )
    available_balances: Mapped[list["AvailableBalance"]] = relationship(
        "AvailableBalance",
        back_populates="product",
    )
