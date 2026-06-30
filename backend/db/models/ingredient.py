from datetime import date, datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.connection import Base

if TYPE_CHECKING:
    from db.models.recipe import RecipeIngredient


class IngredientType(StrEnum):
    SYRUP = "syrup"
    WATER = "water"
    CO2 = "co2"
    PACKAGING = "packaging"


class Ingredient(Base):
    """Raw materials and consumables — no foreign keys."""

    __tablename__ = "ingredients"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    ingredient_type: Mapped[str] = mapped_column(String(32), nullable=False)
    lot_number: Mapped[str | None] = mapped_column(String(64))
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    supplier: Mapped[str | None] = mapped_column(String(255))
    expires_at: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    recipe_lines: Mapped[list["RecipeIngredient"]] = relationship(back_populates="ingredient")

    def __repr__(self) -> str:
        return (
            f"Ingredient(id={self.id!r}, name={self.name!r}, "
            f"ingredient_type={self.ingredient_type!r})"
        )
