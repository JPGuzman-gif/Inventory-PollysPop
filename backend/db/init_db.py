"""Create all tables defined on Base.metadata."""

from db.connection import Base, engine
from db.models import Ingredient, Product, Recipe, RecipeIngredient  # noqa: F401 — register models


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
    print("Tables created:", ", ".join(sorted(Base.metadata.tables.keys())))
