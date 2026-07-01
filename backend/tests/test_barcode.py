import pytest

from app.services.barcode import (
    allocate_pallet_barcode,
    generate_pallet_barcode,
    parse_pallet_barcode,
    render_barcode_svg,
)


def test_generate_pallet_barcode_formats_global_sequence() -> None:
    assert generate_pallet_barcode(1) == "00001"
    assert generate_pallet_barcode(42) == "00042"
    assert generate_pallet_barcode(12345) == "12345"


def test_generate_pallet_barcode_rejects_invalid_pallet_number() -> None:
    with pytest.raises(ValueError, match="pallet_number"):
        generate_pallet_barcode(0)


def test_parse_pallet_barcode_round_trip() -> None:
    for pallet_number in (1, 3, 99999):
        barcode = generate_pallet_barcode(pallet_number)
        assert parse_pallet_barcode(barcode) == pallet_number


def test_parse_pallet_barcode_rejects_invalid_format() -> None:
    with pytest.raises(ValueError, match="invalid pallet barcode format"):
        parse_pallet_barcode("PP-BC-20260701-00003")
    with pytest.raises(ValueError, match="invalid pallet barcode format"):
        parse_pallet_barcode("1234")


def test_render_barcode_svg_returns_svg_markup() -> None:
    svg = render_barcode_svg("00003")
    assert "<svg" in svg.lower()


class _FakeRow:
    def __init__(self, next_number: int) -> None:
        self.next_number = next_number


class _FakeConnection:
    def __init__(self, next_number: int) -> None:
        self.next_number = next_number

    def execute(self, _statement, params=None):
        return self

    def one(self):
        return _FakeRow(self.next_number)


def test_allocate_pallet_barcode_uses_global_database_sequence() -> None:
    connection = _FakeConnection(next_number=4)
    pallet_number, barcode = allocate_pallet_barcode(connection)
    assert pallet_number == 4
    assert barcode == "00004"
