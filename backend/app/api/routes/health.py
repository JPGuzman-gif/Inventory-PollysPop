from fastapi import APIRouter
from fastapi.responses import JSONResponse

from db.connection import check_connection, get_dialect_name

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check():
    db_ok, db_message = check_connection()
    payload = {
        "status": "ok" if db_ok else "degraded",
        "database": {
            "dialect": get_dialect_name(),
            "status": "connected" if db_ok else "unavailable",
            "detail": db_message,
        },
    }
    if not db_ok:
        return JSONResponse(status_code=503, content=payload)
    return payload
