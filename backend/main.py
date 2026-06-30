from fastapi import FastAPI

from app.api.routes import health
from app.config import APP_NAME, DEBUG
from db.connection import get_db  # noqa: F401 — FastAPI dependency, used by future routes

app = FastAPI(
    title=APP_NAME,
    description=(
        "Production and inventory tracking for Polly's Pop. "
        "Phase 1: manual pallet registration and inventory movement input."
    ),
    debug=DEBUG,
)

app.include_router(health.router)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Polly's Pop API", "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
