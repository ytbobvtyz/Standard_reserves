from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.available_balance import AvailableBalance
    from app.models.normative import Normative
    from app.models.product import Product
    from app.models.request_item import RequestItem


class Object(TimestampMixin, SoftDeleteMixin, Base):
    """Plant or warehouse (table name: objects)."""

    __tablename__ = "objects"
    __table_args__ = (
        CheckConstraint("type IN ('plant', 'warehouse')", name="ck_objects_type"),
        Index("idx_objects_type", "type"),
        Index("idx_objects_city", "city"),
    )

    code: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    city: Mapped[str] = mapped_column(Text, nullable=False)
    region: Mapped[str | None] = mapped_column(Text)
    address: Mapped[str | None] = mapped_column(Text)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    products_as_plant: Mapped[list["Product"]] = relationship(
        "Product",
        back_populates="plant",
        foreign_keys="Product.plant_id",
    )
    request_items: Mapped[list["RequestItem"]] = relationship(
        "RequestItem",
        back_populates="warehouse",
    )
    normatives: Mapped[list["Normative"]] = relationship(
        "Normative",
        back_populates="warehouse",
    )
    available_balances: Mapped[list["AvailableBalance"]] = relationship(
        "AvailableBalance",
        back_populates="warehouse",
    )
