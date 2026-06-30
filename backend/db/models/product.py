from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.connection import Base

if TYPE_CHECKING:
    from db.models.recipe import Recipe


class Product(Base):
    """Finished soda catalog — no foreign keys."""

    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint(
            "flavor_code ~ '^[A-Z]{3}$'",
            name="ck_products_flavor_code_format",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    flavor_code: Mapped[str] = mapped_column(String(3), nullable=False, unique=True)
    sku: Mapped[str | None] = mapped_column(String(64), unique=True)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    recipes: Mapped[list["Recipe"]] = relationship(back_populates="product")

    def __repr__(self) -> str:
        return f"Product(id={self.id!r}, name={self.name!r}, flavor_code={self.flavor_code!r})"
