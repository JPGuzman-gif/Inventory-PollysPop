from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.engine import Connection

from db.connection import get_db

router = APIRouter(tags=["products"])


@router.get("/products")
def list_products(
    brand_id: int | None = Query(default=None),
    db: Connection = Depends(get_db),
) -> list[dict]:
    query = """
        SELECT id, name, flavor_code, is_diet
        FROM products
        WHERE is_active = TRUE
    """
    params: dict = {}

    if brand_id is not None:
        query += " AND brand_id = :brand_id"
        params["brand_id"] = brand_id

    query += " ORDER BY name"
    rows = db.execute(text(query), params).fetchall()
    return [dict(row._mapping) for row in rows]
