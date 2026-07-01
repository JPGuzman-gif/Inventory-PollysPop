import csv
import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.engine import Connection

from db.connection import get_db

router = APIRouter(tags=["export"])


@router.get("/export/sold-products.csv")
def export_sold_products(db: Connection = Depends(get_db)) -> StreamingResponse:
    rows = db.execute(
        text(
            """
            SELECT
                brand_name,
                flavor_name,
                expiration_date,
                sold_from_location,
                sold_at
            FROM sold_products
            ORDER BY sold_at
            """
        ),
    ).fetchall()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        ["brand_name", "flavor_name", "expiration_date", "sold_from_location", "sold_at"]
    )

    for row in rows:
        data = row._mapping
        writer.writerow(
            [
                data["brand_name"],
                data["flavor_name"],
                data["expiration_date"].isoformat()
                if data["expiration_date"]
                else "",
                data["sold_from_location"],
                data["sold_at"].isoformat() if data["sold_at"] else "",
            ]
        )

    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="sold-products.csv"'},
    )
