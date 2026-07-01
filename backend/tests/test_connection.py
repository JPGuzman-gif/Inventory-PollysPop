import pytest

from db.connection import (
    check_connection,
    get_dialect_name,
    is_postgresql,
    is_sqlite,
    normalize_database_url,
    require_postgresql,
)


def test_normalize_postgres_scheme() -> None:
    url = "postgres://user:pass@localhost:5432/pollyspop"
    assert normalize_database_url(url) == (
        "postgresql+psycopg2://user:pass@localhost:5432/pollyspop"
    )


def test_normalize_postgresql_without_driver() -> None:
    url = "postgresql://user:pass@localhost:5432/pollyspop"
    assert normalize_database_url(url) == (
        "postgresql+psycopg2://user:pass@localhost:5432/pollyspop"
    )


def test_normalize_preserves_psycopg2_url() -> None:
    url = "postgresql+psycopg2://user:pass@localhost:5432/pollyspop"
    assert normalize_database_url(url) == url


def test_get_dialect_name() -> None:
    assert get_dialect_name("postgresql+psycopg2://localhost/pollyspop") == "postgresql"
    assert get_dialect_name("sqlite:///./data/pollyspop.db") == "sqlite"


def test_is_postgresql_and_sqlite() -> None:
    assert is_postgresql("postgresql+psycopg2://localhost/pollyspop")
    assert not is_postgresql("sqlite:///./data/pollyspop.db")
    assert is_sqlite("sqlite:///./data/pollyspop.db")
    assert not is_sqlite("postgresql+psycopg2://localhost/pollyspop")


def test_require_postgresql_rejects_sqlite() -> None:
    with pytest.raises(RuntimeError, match="requires PostgreSQL"):
        require_postgresql("sqlite:///./data/pollyspop.db")


def test_check_connection_sqlite_in_memory() -> None:
    from sqlalchemy import create_engine

    in_memory = create_engine("sqlite:///:memory:")
    ok, message = check_connection(in_memory)
    assert ok is True
    assert message == "connected"
