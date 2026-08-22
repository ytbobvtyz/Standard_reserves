from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
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
    from app.models.product import Product
    from app.models.request_item import RequestItem
    from app.models.user import User


class Object(TimestampMixin, SoftDeleteMixin, Base):
    """Plant or warehouse (table name: objects)."""

    __tablename__ = "objects"
    __table_args__ = (
        CheckConstraint("type IN ('plant', 'warehouse')", name="ck_objects_type"),
        Index("idx_objects_type", "type"),
        Index("idx_objects_city", "city"),
        Index("idx_objects_last_modified_at", "last_modified_at"),
        Index("idx_objects_last_modified_by", "last_modified_by"),
        Index(
            "idx_objects_erp_plant_code",
            "erp_plant_code",
            postgresql_where=text("erp_plant_code IS NOT NULL"),
        ),
        Index(
            "idx_objects_erp_warehouse_code",
            "erp_warehouse_code",
            postgresql_where=text("erp_warehouse_code IS NOT NULL"),
        ),
        Index(
            "uq_objects_loading_point",
            "loading_point",
            unique=True,
            postgresql_where=text(
                "loading_point IS NOT NULL AND deleted_at IS NULL"
            ),
        ),
    )

    code: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    city: Mapped[str] = mapped_column(Text, nullable=False)
    region: Mapped[str | None] = mapped_column(Text)
    address: Mapped[str | None] = mapped_column(Text)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    erp_plant_code: Mapped[int | None] = mapped_column(Integer)
    erp_warehouse_code: Mapped[str | None] = mapped_column(String(4))
    loading_point: Mapped[str | None] = mapped_column(String(4))
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    last_modified_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id"),
    )
    last_modified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

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
    modified_by_user: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[last_modified_by],
    )
