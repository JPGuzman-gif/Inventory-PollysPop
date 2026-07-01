from datetime import date

import pytest

from app.services.barcode import (
    allocate_barcode,
    generate_barcode,
    parse_barcode,
    render_barcode_svg,
)


def test_generate_barcode_formats_provisional_string() -> None:
    assert generate_barcode("BC", date(2026, 7, 1), 3) == "PP-BC-20260701-003"


def test_generate_barcode_normalizes_flavor_code() -> None:
    assert generate_barcode(" drb ", date(2026, 1, 15), 12) == "PP-DRB-20260115-012"


def test_generate_barcode_rejects_invalid_pallet_number() -> None:
    with pytest.raises(ValueError, match="pallet_number"):
        generate_barcode("BC", date(2026, 7, 1), 0)


def test_parse_barcode_round_trip() -> None:
    barcode = "PP-BC-20260701-003"
    flavor_code, bottled_at, pallet_number = parse_barcode(barcode)
    assert flavor_code == "BC"
    assert bottled_at == date(2026, 7, 1)
    assert pallet_number == 3
    assert generate_barcode(flavor_code, bottled_at, pallet_number) == barcode


def test_parse_barcode_rejects_invalid_format() -> None:
    with pytest.raises(ValueError, match="invalid barcode format"):
        parse_barcode("INVALID")


def test_render_barcode_svg_returns_svg_markup() -> None:
    svg = render_barcode_svg("PP-BC-20260701-003")
    assert "<svg" in svg.lower()


class _FakeRow:
    def __init__(self, next_number: int) -> None:
        self.next_number = next_number


class _FakeConnection:
    def __init__(self, next_number: int) -> None:
        self.next_number = next_number
        self.last_params: dict | None = None

    def execute(self, _statement, params=None):
        self.last_params = params
        return self

    def one(self):
        return _FakeRow(self.next_number)


def test_allocate_barcode_uses_database_sequence() -> None:
    connection = _FakeConnection(next_number=4)
    pallet_number, barcode = allocate_barcode(
        connection,
        flavor_code="ST",
        product_id=7,
        bottled_at=date(2026, 7, 1),
    )
    assert pallet_number == 4
    assert barcode == "PP-ST-20260701-004"
    assert connection.last_params == {
        "product_id": 7,
        "bottled_at": date(2026, 7, 1),
    }
