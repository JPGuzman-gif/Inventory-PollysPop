from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.connection import Base

if TYPE_CHECKING:
    from db.models.ingredient import Ingredient
    from db.models.product import Product
    from db.models.production_batch import ProductionBatch


class MovementType(StrEnum):
    PRODUCTION_IN = "production_in"
    PRODUCTION_OUT = "production_out"
    SALE_OUT = "sale_out"
    RECEIPT_IN = "receipt_in"
    ADJUSTMENT = "adjustment"


class InventoryMovement(Base):
    """Append-only audit log of every stock change."""

    __tablename__ = "inventory_movements"
    __table_args__ = (
        CheckConstraint(
            "(product_id IS NOT NULL AND ingredient_id IS NULL) OR "
            "(product_id IS NULL AND ingredient_id IS NOT NULL)",
            name="ck_inventory_movements_one_item_fk",
        ),
        CheckConstraint(
            "movement_type IN ('production_in', 'production_out', 'sale_out', 'receipt_in', 'adjustment')",
            name="ck_inventory_movements_type",
        ),
        CheckConstraint(
            "movement_type != 'production_in' OR product_id IS NOT NULL",
            name="ck_inventory_movements_production_in_product",
        ),
        CheckConstraint(
            "movement_type != 'production_out' OR ingredient_id IS NOT NULL",
            name="ck_inventory_movements_production_out_ingredient",
        ),
        CheckConstraint(
            "movement_type != 'sale_out' OR (product_id IS NOT NULL AND production_batch_id IS NULL)",
            name="ck_inventory_movements_sale_out_product",
        ),
        CheckConstraint(
            "movement_type NOT IN ('production_in', 'production_out') OR production_batch_id IS NOT NULL",
            name="ck_inventory_movements_production_batch_required",
        ),
        CheckConstraint(
            "movement_type != 'production_in' OR quantity_delta > 0",
            name="ck_inventory_movements_production_in_positive",
        ),
        CheckConstraint(
            "movement_type != 'production_out' OR quantity_delta < 0",
            name="ck_inventory_movements_production_out_negative",
        ),
        CheckConstraint(
            "movement_type != 'sale_out' OR quantity_delta < 0",
            name="ck_inventory_movements_sale_out_negative",
        ),
        CheckConstraint(
            "movement_type != 'receipt_in' OR quantity_delta > 0",
            name="ck_inventory_movements_receipt_in_positive",
        ),
        CheckConstraint(
            "movement_type != 'adjustment' OR (notes IS NOT NULL AND btrim(notes) <> '')",
            name="ck_inventory_movements_adjustment_notes",
        ),
        CheckConstraint(
            "movement_type != 'adjustment' OR quantity_delta <> 0",
            name="ck_inventory_movements_adjustment_nonzero",
        ),
        Index("ix_inventory_movements_production_batch_id", "production_batch_id"),
        Index("ix_inventory_movements_product_created_at", "product_id", "created_at"),
        Index("ix_inventory_movements_ingredient_created_at", "ingredient_id", "created_at"),
        Index("ix_inventory_movements_type_created_at", "movement_type", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    movement_type: Mapped[str] = mapped_column(String(32), nullable=False)
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT")
    )
    ingredient_id: Mapped[int | None] = mapped_column(
        ForeignKey("ingredients.id", ondelete="RESTRICT")
    )
    quantity_delta: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    production_batch_id: Mapped[int | None] = mapped_column(
        ForeignKey("production_batches.id", ondelete="SET NULL")
    )
    reference: Mapped[str | None] = mapped_column(String(128))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[str | None] = mapped_column(String(128))

    product: Mapped["Product | None"] = relationship(back_populates="inventory_movements")
    ingredient: Mapped["Ingredient | None"] = relationship(back_populates="inventory_movements")
    production_batch: Mapped["ProductionBatch | None"] = relationship(
        back_populates="inventory_movements"
    )

    @property
    def item_label(self) -> str:
        """Human-readable item reference for history views."""
        if self.product_id is not None:
            return f"product:{self.product_id}"
        return f"ingredient:{self.ingredient_id}"

    def __repr__(self) -> str:
        return (
            f"InventoryMovement(id={self.id!r}, movement_type={self.movement_type!r}, "
            f"quantity_delta={self.quantity_delta!r}, {self.item_label})"
        )
