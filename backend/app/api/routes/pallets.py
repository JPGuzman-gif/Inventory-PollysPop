from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.engine import Connection

from app.services import pallets as pallet_service
from db.connection import engine, get_db

router = APIRouter(tags=["pallets"])


class CreatePalletRequest(BaseModel):
    product_id: int
    bottled_at: date
    expiration_date: date
    notes: str | None = None


class TransferPalletRequest(BaseModel):
    to_location: str = Field(min_length=1)


def _handle_pallet_error(error: Exception) -> HTTPException:
    if isinstance(error, pallet_service.PalletNotFoundError):
        return HTTPException(status_code=404, detail=str(error))
    if isinstance(error, pallet_service.ProductNotFoundError):
        return HTTPException(status_code=404, detail=str(error))
    if isinstance(error, pallet_service.PalletAlreadySoldError):
        return HTTPException(status_code=409, detail=str(error))
    if isinstance(error, pallet_service.InvalidTransferError):
        return HTTPException(status_code=422, detail=str(error))
    if isinstance(error, ValueError):
        return HTTPException(status_code=422, detail=str(error))
    raise error


@router.get("/pallets/expiring")
def list_expiring_pallets(db: Connection = Depends(get_db)) -> list[dict]:
    return pallet_service.list_expiring_pallets(db)


@router.get("/pallets")
def list_pallets(
    location: str | None = Query(default=None, alias="location"),
    status: str | None = Query(default=None),
    db: Connection = Depends(get_db),
) -> list[dict]:
    return pallet_service.list_pallets(db, location=location, status=status)


@router.post("/pallets", status_code=201)
def create_pallet(body: CreatePalletRequest) -> dict:
    try:
        with engine.begin() as db:
            return pallet_service.create_pallet(
                db,
                product_id=body.product_id,
                bottled_at=body.bottled_at,
                expiration_date=body.expiration_date,
                notes=body.notes,
            )
    except pallet_service.PalletError as error:
        raise _handle_pallet_error(error) from error


@router.get("/pallets/{barcode}")
def get_pallet(barcode: str, db: Connection = Depends(get_db)) -> dict:
    try:
        return pallet_service.get_pallet_by_barcode(db, barcode)
    except pallet_service.PalletError as error:
        raise _handle_pallet_error(error) from error


@router.post("/pallets/{barcode}/transfer")
def transfer_pallet(barcode: str, body: TransferPalletRequest) -> dict:
    try:
        with engine.begin() as db:
            return pallet_service.transfer_pallet(
                db,
                barcode=barcode,
                to_location=body.to_location,
            )
    except pallet_service.PalletError as error:
        raise _handle_pallet_error(error) from error


@router.post("/pallets/{barcode}/sell")
def sell_pallet(barcode: str) -> dict:
    try:
        with engine.begin() as db:
            return pallet_service.sell_pallet(db, barcode=barcode)
    except pallet_service.PalletError as error:
        raise _handle_pallet_error(error) from error
