"""Database engine, URL normalization, and connection helpers."""

from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import SQLAlchemyError

load_dotenv()

DEFAULT_DATABASE_URL = "postgresql+psycopg2://postgres:postgres@localhost:5432/pollyspop"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def normalize_database_url(url: str) -> str:
    """Normalize common DATABASE_URL variants for SQLAlchemy."""
    normalized = url.strip()

    if normalized.startswith("postgres://"):
        normalized = "postgresql+psycopg2://" + normalized[len("postgres://") :]
    elif normalized.startswith("postgresql://") and "+psycopg2" not in normalized:
        normalized = "postgresql+psycopg2://" + normalized[len("postgresql://") :]

    if normalized.startswith("sqlite:///./"):
        relative_path = normalized[len("sqlite:///./") :]
        absolute_path = (Path.cwd() / relative_path).resolve()
        normalized = f"sqlite:///{absolute_path.as_posix()}"

    return normalized


def get_database_url() -> str:
    return normalize_database_url(os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL))


def get_dialect_name(url: str | None = None) -> str:
    parsed = urlparse(url or get_database_url())
    scheme = (parsed.scheme or "").split("+", 1)[0].lower()
    return scheme


def is_postgresql(url: str | None = None) -> bool:
    return get_dialect_name(url) == "postgresql"


def is_sqlite(url: str | None = None) -> bool:
    return get_dialect_name(url) == "sqlite"


def _ensure_data_dir(url: str) -> None:
    if is_sqlite(url):
        DATA_DIR.mkdir(parents=True, exist_ok=True)


def create_db_engine(url: str | None = None) -> Engine:
    database_url = normalize_database_url(url or get_database_url())
    _ensure_data_dir(database_url)

    connect_args: dict = {}
    engine_kwargs: dict = {
        "pool_pre_ping": True,
        "echo": os.getenv("DEBUG", "false").lower() in {"1", "true", "yes"},
    }

    if is_sqlite(database_url):
        connect_args["check_same_thread"] = False
    else:
        engine_kwargs.update(
            {
                "pool_size": int(os.getenv("DB_POOL_SIZE", "5")),
                "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "10")),
            }
        )

    return create_engine(database_url, connect_args=connect_args, **engine_kwargs)


def check_connection(engine: Engine | None = None) -> tuple[bool, str]:
    """Verify the database is reachable. Returns (ok, message)."""
    active_engine = engine or create_db_engine()
    try:
        with active_engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True, "connected"
    except SQLAlchemyError as error:
        dialect = get_dialect_name(str(active_engine.url))
        if dialect == "postgresql":
            hint = (
                "Check that PostgreSQL is running and DATABASE_URL is correct "
                "(host, port, user, password, database name)."
            )
        elif dialect == "sqlite":
            hint = "Check that the SQLite file path is writable."
        else:
            hint = "Verify DATABASE_URL and database server availability."
        return False, f"{error.__class__.__name__}: {error}. {hint}"


def require_postgresql(url: str | None = None) -> None:
    """Raise RuntimeError when the active URL is not PostgreSQL."""
    if not is_postgresql(url):
        raise RuntimeError(
            "schema.sql requires PostgreSQL (SERIAL, TIMESTAMPTZ, regex CHECK constraints). "
            f"Current DATABASE_URL dialect: {get_dialect_name(url)}. "
            "Set DATABASE_URL to a postgresql+psycopg2:// URL in .env."
        )


engine = create_db_engine()


def get_db() -> Generator[Connection, None, None]:
    with engine.connect() as connection:
        yield connection
