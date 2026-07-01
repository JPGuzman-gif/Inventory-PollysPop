"""Pallet inventory operations — create, transfer, sell, and query."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.services.barcode import allocate_pallet_barcode, parse_pallet_barcode

VALID_LOCATIONS = frozenset({"Production Floor", "Warehouse 1", "Warehouse 2"})
EXPIRING_DAYS = 90

_PALLET_SELECT = """
    SELECT
        p.id,
        p.pallet_number,
        p.barcode,
        p.product_id,
        p.expiration_date,
        p.bottled_at,
        p.current_location,
        p.status,
        p.sold_at,
        pr.name AS product_name,
        pr.name AS flavor_name,
        b.name AS brand_name
    FROM pallets p
    JOIN products pr ON pr.id = p.product_id
    JOIN brands b ON b.id = pr.brand_id
"""


class PalletError(Exception):
    """Base error for pallet operations."""


class PalletNotFoundError(PalletError):
    pass


class PalletAlreadySoldError(PalletError):
    pass


class ProductNotFoundError(PalletError):
    pass


class InvalidTransferError(PalletError):
    pass


def _row_to_dict(row) -> dict[str, Any]:
    data = dict(row._mapping)
    for key in ("expiration_date", "bottled_at"):
        if data.get(key) is not None:
            data[key] = data[key].isoformat()
    if data.get("sold_at") is not None:
        data["sold_at"] = data["sold_at"].isoformat()
    return data


def list_pallets(
    connection: Connection,
    *,
    location: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    query = _PALLET_SELECT + " WHERE 1=1"
    params: dict[str, Any] = {}

    if location:
        query += " AND p.current_location = :location"
        params["location"] = location
    if status:
        query += " AND p.status = :status"
        params["status"] = status

    query += " ORDER BY p.barcode"
    rows = connection.execute(text(query), params).fetchall()
    return [_row_to_dict(row) for row in rows]


def _fetch_pallet_row(connection: Connection, barcode: str):
    normalized = barcode.strip()
    parse_pallet_barcode(normalized)

    row = connection.execute(
        text(_PALLET_SELECT + " WHERE p.barcode = :barcode"),
        {"barcode": normalized},
    ).first()

    if row is None:
        raise PalletNotFoundError(f"Pallet not found: {normalized}")
    return row


def get_pallet_by_barcode(connection: Connection, barcode: str) -> dict[str, Any]:
    return _row_to_dict(_fetch_pallet_row(connection, barcode))


def list_expiring_pallets(
    connection: Connection,
    *,
    days: int = EXPIRING_DAYS,
) -> list[dict[str, Any]]:
    threshold = date.today() + timedelta(days=days)
    rows = connection.execute(
        text(
            _PALLET_SELECT
            + """
            WHERE p.status = 'active'
              AND p.expiration_date <= :threshold
            ORDER BY p.expiration_date, p.barcode
            """
        ),
        {"threshold": threshold},
    ).fetchall()
    return [_row_to_dict(row) for row in rows]


def _get_product(connection: Connection, product_id: int) -> dict[str, Any]:
    row = connection.execute(
        text(
            """
            SELECT p.id, p.name, b.name AS brand_name
            FROM products p
            JOIN brands b ON b.id = p.brand_id
            WHERE p.id = :product_id AND p.is_active = TRUE
            """
        ),
        {"product_id": product_id},
    ).first()

    if row is None:
        raise ProductNotFoundError(f"Product not found: {product_id}")
    return dict(row._mapping)


def create_pallet(
    connection: Connection,
    *,
    product_id: int,
    bottled_at: date,
    expiration_date: date,
    notes: str | None = None,
) -> dict[str, Any]:
    _get_product(connection, product_id)
    pallet_number, barcode = allocate_pallet_barcode(connection)

    row = connection.execute(
        text(
            """
            INSERT INTO pallets (
                pallet_number, barcode, product_id,
                expiration_date, bottled_at, current_location, status
            )
            VALUES (
                :pallet_number, :barcode, :product_id,
                :expiration_date, :bottled_at, 'Production Floor', 'active'
            )
            RETURNING id
            """
        ),
        {
            "pallet_number": pallet_number,
            "barcode": barcode,
            "product_id": product_id,
            "expiration_date": expiration_date,
            "bottled_at": bottled_at,
        },
    ).one()

    connection.execute(
        text(
            """
            INSERT INTO inventory_movements (
                pallet_id, movement_type, from_location, to_location, notes
            )
            VALUES (:pallet_id, 'create', NULL, 'Production Floor', :notes)
            """
        ),
        {"pallet_id": row.id, "notes": notes},
    )

    return get_pallet_by_barcode(connection, barcode)


def transfer_pallet(
    connection: Connection,
    *,
    barcode: str,
    to_location: str,
) -> dict[str, Any]:
    if to_location not in VALID_LOCATIONS:
        raise InvalidTransferError(f"Invalid location: {to_location}")

    row = _fetch_pallet_row(connection, barcode)
    pallet = dict(row._mapping)

    if pallet["status"] == "sold":
        raise PalletAlreadySoldError(f"Pallet {barcode} is already sold")

    from_location = pallet["current_location"]
    if from_location == to_location:
        raise InvalidTransferError(f"Pallet is already at {to_location}")

    connection.execute(
        text(
            """
            UPDATE pallets
            SET current_location = :to_location
            WHERE barcode = :barcode
            """
        ),
        {"to_location": to_location, "barcode": pallet["barcode"]},
    )

    connection.execute(
        text(
            """
            INSERT INTO inventory_movements (
                pallet_id, movement_type, from_location, to_location
            )
            VALUES (:pallet_id, 'transfer', :from_location, :to_location)
            """
        ),
        {
            "pallet_id": pallet["id"],
            "from_location": from_location,
            "to_location": to_location,
        },
    )

    return get_pallet_by_barcode(connection, pallet["barcode"])


def sell_pallet(connection: Connection, *, barcode: str) -> dict[str, Any]:
    row = _fetch_pallet_row(connection, barcode)
    pallet = dict(row._mapping)

    if pallet["status"] == "sold":
        raise PalletAlreadySoldError(f"Pallet {barcode} is already sold")

    sold_from = pallet["current_location"]

    connection.execute(
        text(
            """
            UPDATE pallets
            SET status = 'sold', sold_at = NOW()
            WHERE barcode = :barcode
            """
        ),
        {"barcode": pallet["barcode"]},
    )

    connection.execute(
        text(
            """
            INSERT INTO sold_products (
                pallet_id, product_id, brand_name, flavor_name,
                expiration_date, sold_from_location
            )
            VALUES (
                :pallet_id, :product_id, :brand_name, :flavor_name,
                :expiration_date, :sold_from_location
            )
            """
        ),
        {
            "pallet_id": pallet["id"],
            "product_id": pallet["product_id"],
            "brand_name": pallet["brand_name"],
            "flavor_name": pallet["product_name"],
            "expiration_date": pallet["expiration_date"],
            "sold_from_location": sold_from,
        },
    )

    connection.execute(
        text(
            """
            INSERT INTO inventory_movements (
                pallet_id, movement_type, from_location, to_location
            )
            VALUES (:pallet_id, 'sell', :from_location, NULL)
            """
        ),
        {"pallet_id": pallet["id"], "from_location": sold_from},
    )

    return get_pallet_by_barcode(connection, pallet["barcode"])
