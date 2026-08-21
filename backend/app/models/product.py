from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    CHAR,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.available_balance import AvailableBalance
    from app.models.normative import Normative
    from app.models.object import Object
    from app.models.request_item import RequestItem
    from app.models.user import User


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
        Index(
            "idx_products_gtin",
            "gtin",
            postgresql_where=text("gtin IS NOT NULL"),
        ),
        Index("idx_products_last_modified_at", "last_modified_at"),
        Index("idx_products_last_modified_by", "last_modified_by"),
        CheckConstraint(
            "gtin IS NULL OR gtin ~ '^[0-9]{13}$'",
            name="ck_products_gtin",
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
    parent_code: Mapped[int | None] = mapped_column(Integer)
    children_code: Mapped[int | None] = mapped_column(Integer)
    gtin: Mapped[str | None] = mapped_column(String(13))
    mark_control: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    last_modified_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id"),
    )
    last_modified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

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
        primaryjoin="foreign(Product.parent_code)==remote(Product.code)",
        foreign_keys=[parent_code],
        remote_side=[code],
        uselist=False,
    )
    child: Mapped["Product | None"] = relationship(
        "Product",
        primaryjoin="foreign(Product.children_code)==remote(Product.code)",
        foreign_keys=[children_code],
        remote_side=[code],
        uselist=False,
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
    modified_by_user: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[last_modified_by],
    )
