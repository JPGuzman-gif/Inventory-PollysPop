from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    select,
)
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship

from db.connection import Base

if TYPE_CHECKING:
    from db.models.inventory_movement import InventoryMovement
    from db.models.product import Product
    from db.models.recipe import Recipe

BATCH_CODE_PATTERN = re.compile(r"^(\d{6})-([A-Z]{3})-(\d{3})$")


class BatchStatus(StrEnum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PalletConfigurationType(StrEnum):
    FOUR_PACK = "4-pack"
    SEPARATOR = "separator"


def format_batch_code(production_date: date, flavor_code: str, sequence_number: int) -> str:
    """Build smart batch ID: YYMMDD-FLV-SEQ (e.g. 250630-CHR-001)."""
    return f"{production_date.strftime('%y%m%d')}-{flavor_code}-{sequence_number:03d}"


def parse_batch_code(batch_code: str) -> tuple[date, str, int]:
    """Parse a batch code into production date, flavor code, and sequence number."""
    match = BATCH_CODE_PATTERN.match(batch_code)
    if not match:
        raise ValueError(f"Invalid batch code format: {batch_code!r}")

    date_part, flavor_code, seq_part = match.groups()
    production_date = datetime.strptime(date_part, "%y%m%d").date()
    return production_date, flavor_code, int(seq_part)


def next_sequence_number(
    session: Session,
    *,
    production_date: date,
    flavor_code: str,
) -> int:
    """Return the next daily sequence for a flavor (001, 002, …)."""
    current_max = session.scalar(
        select(func.max(ProductionBatch.sequence_number)).where(
            ProductionBatch.production_date == production_date,
            ProductionBatch.flavor_code == flavor_code,
        )
    )
    return (current_max or 0) + 1


class ProductionBatch(Base):
    """Production run with smart batch ID components and product/recipe traceability."""

    __tablename__ = "production_batches"
    __table_args__ = (
        UniqueConstraint("batch_code", name="uq_production_batches_batch_code"),
        UniqueConstraint(
            "production_date",
            "flavor_code",
            "sequence_number",
            name="uq_production_batches_date_flavor_seq",
        ),
        CheckConstraint(
            "flavor_code ~ '^[A-Z]{3}$'",
            name="ck_production_batches_flavor_code_format",
        ),
        CheckConstraint(
            "sequence_number >= 1",
            name="ck_production_batches_sequence_positive",
        ),
        CheckConstraint(
            "pallet_configuration IN ('4-pack', 'separator')",
            name="ck_production_batches_pallet_configuration",
        ),
        CheckConstraint(
            "status IN ('planned', 'in_progress', 'completed', 'cancelled')",
            name="ck_production_batches_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    batch_code: Mapped[str] = mapped_column(String(16), nullable=False)
    production_date: Mapped[date] = mapped_column(Date, nullable=False)
    flavor_code: Mapped[str] = mapped_column(String(3), nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    expiration_date: Mapped[date] = mapped_column(Date, nullable=False)
    pallet_configuration: Mapped[str] = mapped_column(String(16), nullable=False)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    recipe_id: Mapped[int] = mapped_column(
        ForeignKey("recipes.id", ondelete="RESTRICT"), nullable=False
    )
    quantity_produced: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    produced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=BatchStatus.PLANNED, server_default="planned"
    )
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    product: Mapped["Product"] = relationship(back_populates="production_batches")
    recipe: Mapped["Recipe"] = relationship(back_populates="production_batches")
    inventory_movements: Mapped[list["InventoryMovement"]] = relationship(
        back_populates="production_batch"
    )

    @classmethod
    def assign_batch_identity(
        cls,
        session: Session,
        *,
        product: Product,
        production_date: date,
        sequence_number: int | None = None,
    ) -> tuple[str, str, int]:
        """Resolve flavor code and sequence, returning (batch_code, flavor_code, sequence_number)."""
        flavor_code = product.flavor_code
        seq = sequence_number or next_sequence_number(
            session,
            production_date=production_date,
            flavor_code=flavor_code,
        )
        batch_code = format_batch_code(production_date, flavor_code, seq)
        return batch_code, flavor_code, seq

    def sync_batch_code(self) -> None:
        """Recompute batch_code from stored date, flavor, and sequence components."""
        self.batch_code = format_batch_code(
            self.production_date, self.flavor_code, self.sequence_number
        )

    def __repr__(self) -> str:
        return (
            f"ProductionBatch(id={self.id!r}, batch_code={self.batch_code!r}, "
            f"status={self.status!r})"
        )
