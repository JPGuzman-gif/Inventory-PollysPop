"""Apply CREATE TABLE statements from schema.sql."""

from pathlib import Path

from sqlalchemy import text

from db.connection import engine

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


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


def init_db() -> None:
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    statements = _executable_statements(sql)

    if not statements:
        print("schema.sql has no statements yet — add CREATE TABLE SQL and re-run.")
        return

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))

    print(f"Applied {len(statements)} statement(s) from schema.sql.")


if __name__ == "__main__":
    init_db()
