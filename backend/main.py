from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import brands, export, health, pallets, products
from app.config import APP_NAME, DEBUG
from db.connection import get_db  # noqa: F401 — FastAPI dependency for route handlers

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

app = FastAPI(
    title=APP_NAME,
    description=(
        "Production and inventory tracking for Polly's Pop. "
        "Phase 1: manual pallet registration and inventory movement input."
    ),
    debug=DEBUG,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(brands.router)
app.include_router(products.router)
app.include_router(pallets.router)
app.include_router(export.router)

if FRONTEND_DIR.is_dir():
    app.mount("/app", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


@app.get("/")
def root() -> RedirectResponse:
    return RedirectResponse(url="/app/")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
