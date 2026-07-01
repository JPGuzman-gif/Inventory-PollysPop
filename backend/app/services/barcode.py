"""Pallet barcode generation.

This system generates pallet numbers only. Bottle, 4-pack, and case UPCs are
third-party codes stored as reference data on `products` — never generated here.

Format: {pallet_seq} — global counter zero-padded to 5 digits.
Examples: 00001, 00002, 00003

Adjust this module when Cole provides the final pallet label format.
"""

from __future__ import annotations

import io
import re

from barcode import Code128
from barcode.writer import SVGWriter
from sqlalchemy import text
from sqlalchemy.engine import Connection

PALLET_SEQ_WIDTH = 5

PALLET_BARCODE_PATTERN = re.compile(rf"^\d{{{PALLET_SEQ_WIDTH}}}$")


def format_pallet_sequence(pallet_number: int) -> str:
    if pallet_number < 1:
        raise ValueError("pallet_number must be >= 1")
    return str(pallet_number).zfill(PALLET_SEQ_WIDTH)


def generate_pallet_barcode(pallet_number: int) -> str:
    """Build the scannable pallet barcode string (sequence number only)."""
    barcode = format_pallet_sequence(pallet_number)
    if not PALLET_BARCODE_PATTERN.match(barcode):
        raise ValueError(f"generated barcode does not match expected format: {barcode}")
    return barcode


def parse_pallet_barcode(barcode: str) -> int:
    """Parse a pallet barcode into its numeric pallet number."""
    normalized = barcode.strip()
    if not PALLET_BARCODE_PATTERN.match(normalized):
        raise ValueError(f"invalid pallet barcode format: {barcode}")
    return int(normalized)


def get_next_pallet_number(connection: Connection) -> int:
    """Return the next global pallet number (1, 2, 3, ...)."""
    row = connection.execute(
        text(
            """
            SELECT COALESCE(MAX(pallet_number), 0) + 1 AS next_number
            FROM pallets
            """
        ),
    ).one()
    return int(row.next_number)


def allocate_pallet_barcode(connection: Connection) -> tuple[int, str]:
    """Reserve the next pallet number and return (pallet_number, barcode)."""
    pallet_number = get_next_pallet_number(connection)
    barcode = generate_pallet_barcode(pallet_number)
    return pallet_number, barcode


def render_barcode_svg(barcode: str) -> str:
    """Render a Code128 SVG for printing or browser display."""
    buffer = io.BytesIO()
    Code128(barcode, writer=SVGWriter()).write(buffer, options={"write_text": True})
    return buffer.getvalue().decode("utf-8")
