import os
from collections.abc import Generator
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Connection, Engine

load_dotenv()

DEFAULT_DATABASE_URL = "sqlite:///./data/pollyspop.db"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def get_database_url() -> str:
    return os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


def _ensure_data_dir(url: str) -> None:
    if url.startswith("sqlite"):
        DATA_DIR.mkdir(parents=True, exist_ok=True)


def create_db_engine(url: str | None = None) -> Engine:
    database_url = url or get_database_url()
    _ensure_data_dir(database_url)

    connect_args = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    return create_engine(database_url, connect_args=connect_args)


engine = create_db_engine()


def get_db() -> Generator[Connection, None, None]:
    with engine.connect() as connection:
        yield connection
