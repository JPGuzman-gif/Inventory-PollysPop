from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.engine import Connection

from db.connection import get_db

router = APIRouter(tags=["brands"])


@router.get("/brands")
def list_brands(db: Connection = Depends(get_db)) -> list[dict]:
    rows = db.execute(
        text(
            """
            SELECT id, name
            FROM brands
            WHERE is_active = TRUE
            ORDER BY name
            """
        ),
    ).fetchall()
    return [dict(row._mapping) for row in rows]
