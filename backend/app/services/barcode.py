"""Provisional pallet barcode generation.

Format: PP-{flavor_code}-{YYYYMMDD}-{pallet_seq}
Example: PP-BC-20260701-003

Adjust this module when Cole provides the final label format (feature/08-barcode-adjust).
"""

from __future__ import annotations

import io
import re
from datetime import date

from barcode import Code128
from barcode.writer import SVGWriter
from sqlalchemy import text
from sqlalchemy.engine import Connection

BARCODE_PREFIX = "PP"
DATE_FORMAT = "%Y%m%d"
PALLET_SEQ_WIDTH = 3

BARCODE_PATTERN = re.compile(
    rf"^{BARCODE_PREFIX}-[A-Z0-9]{{2,10}}-\d{{8}}-\d{{{PALLET_SEQ_WIDTH}}}$"
)


def format_bottling_date(bottled_at: date) -> str:
    return bottled_at.strftime(DATE_FORMAT)


def format_pallet_sequence(pallet_number: int) -> str:
    if pallet_number < 1:
        raise ValueError("pallet_number must be >= 1")
    return str(pallet_number).zfill(PALLET_SEQ_WIDTH)


def generate_barcode(flavor_code: str, bottled_at: date, pallet_number: int) -> str:
    """Build the human-readable pallet barcode string."""
    normalized = flavor_code.upper().strip()
    if not normalized:
        raise ValueError("flavor_code is required")

    barcode = (
        f"{BARCODE_PREFIX}-{normalized}-"
        f"{format_bottling_date(bottled_at)}-"
        f"{format_pallet_sequence(pallet_number)}"
    )
    if not BARCODE_PATTERN.match(barcode):
        raise ValueError(f"generated barcode does not match expected format: {barcode}")
    return barcode


def parse_barcode(barcode: str) -> tuple[str, date, int]:
    """Parse a provisional barcode into flavor code, bottling date, and pallet number."""
    normalized = barcode.strip().upper()
    if not BARCODE_PATTERN.match(normalized):
        raise ValueError(f"invalid barcode format: {barcode}")

    _, flavor_code, date_part, seq_part = normalized.split("-")
    bottled_at = date.fromisoformat(
        f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]}"
    )
    return flavor_code, bottled_at, int(seq_part)


def get_next_pallet_number(
    connection: Connection, product_id: int, bottled_at: date
) -> int:
    """Return the next sequential pallet number for a product on a bottling date."""
    row = connection.execute(
        text(
            """
            SELECT COALESCE(MAX(pallet_number), 0) + 1 AS next_number
            FROM pallets
            WHERE product_id = :product_id
              AND bottled_at = :bottled_at
            """
        ),
        {"product_id": product_id, "bottled_at": bottled_at},
    ).one()
    return int(row.next_number)


def allocate_barcode(
    connection: Connection,
    flavor_code: str,
    product_id: int,
    bottled_at: date,
) -> tuple[int, str]:
    """Reserve the next pallet number and return (pallet_number, barcode)."""
    pallet_number = get_next_pallet_number(connection, product_id, bottled_at)
    barcode = generate_barcode(flavor_code, bottled_at, pallet_number)
    return pallet_number, barcode


def render_barcode_svg(barcode: str) -> str:
    """Render a Code128 SVG for printing or browser display."""
    buffer = io.BytesIO()
    Code128(barcode, writer=SVGWriter()).write(buffer, options={"write_text": True})
    return buffer.getvalue().decode("utf-8")
