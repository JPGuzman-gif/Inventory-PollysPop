"""Apply CREATE TABLE statements from schema.sql and optional seed data."""

import argparse
from pathlib import Path

from sqlalchemy import text

from db.connection import engine

DB_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = DB_DIR / "schema.sql"
SEED_PATH = DB_DIR / "seed.sql"

# Child tables first. Includes legacy ORM prototype tables for clean resets.
DROP_ORDER = (
    "notifications",
    "sold_products",
    "inventory_movements",
    "pallets",
    "production_batches",
    "products",
    "recipe_ingredients",
    "recipes",
    "ingredients",
    "brands",
)


def _executable_statements(sql: str) -> list[str]:
    lines = []
    for line in sql.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        lines.append(line)

    if not lines:
        return []

    combined = "\n".join(lines)
    return [statement.strip() for statement in combined.split(";") if statement.strip()]


def _apply_sql_file(path: Path) -> int:
    sql = path.read_text(encoding="utf-8")
    statements = _executable_statements(sql)

    if not statements:
        print(f"{path.name} has no statements — skipping.")
        return 0

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))

    print(f"Applied {len(statements)} statement(s) from {path.name}.")
    return len(statements)


def reset_db() -> None:
    """Drop all known tables (including legacy prototype) and reapply schema + seed."""
    with engine.begin() as connection:
        for table in DROP_ORDER:
            connection.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))

    print(f"Dropped {len(DROP_ORDER)} table(s) (if present).")
    init_db()


def init_db() -> None:
    if not SCHEMA_PATH.exists():
        print("schema.sql not found — add CREATE TABLE SQL and re-run.")
        return

    schema_count = _apply_sql_file(SCHEMA_PATH)

    if schema_count == 0:
        print("schema.sql has no statements yet — add CREATE TABLE SQL and re-run.")
        return

    if SEED_PATH.exists():
        _apply_sql_file(SEED_PATH)
    else:
        print("No seed.sql found — skipping seed data.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize or reset the database.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop all tables (including legacy ORM prototype) and recreate from schema.sql",
    )
    args = parser.parse_args()

    if args.reset:
        reset_db()
    else:
        init_db()
