"""Create all tables defined on Base.metadata."""

from db.connection import Base, engine
from db.models import (  # noqa: F401 — register models
    Ingredient,
    InventoryMovement,
    Product,
    ProductionBatch,
    Recipe,
    RecipeIngredient,
)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
    print("Tables created:", ", ".join(sorted(Base.metadata.tables.keys())))
