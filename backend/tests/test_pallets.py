"""Tests for pallet service logic with a mocked connection."""

from datetime import date
from unittest.mock import MagicMock

import pytest

from app.services import pallets as pallet_service
from app.services.pallets import (
    InvalidTransferError,
    PalletAlreadySoldError,
    PalletNotFoundError,
    ProductNotFoundError,
)


class _FakeRow:
    def __init__(self, **kwargs) -> None:
        self._data = kwargs

    @property
    def _mapping(self):
        return self._data


class _FakeResult:
    def __init__(self, rows=None, one_row=None) -> None:
        self._rows = rows or []
        self._one_row = one_row

    def fetchall(self):
        return self._rows

    def first(self):
        if self._one_row is not None:
            return self._one_row
        return self._rows[0] if self._rows else None

    def one(self):
        return self._one_row


def _pallet_row(**overrides):
    data = {
        "id": 1,
        "pallet_number": 1,
        "barcode": "00001",
        "product_id": 10,
        "expiration_date": date(2027, 7, 1),
        "bottled_at": date(2026, 7, 1),
        "current_location": "Production Floor",
        "status": "active",
        "sold_at": None,
        "product_name": "Root Beer",
        "flavor_name": "Root Beer",
        "brand_name": "Polly's Pop",
    }
    data.update(overrides)
    return _FakeRow(**data)


def test_get_pallet_by_barcode_returns_serialized_dates() -> None:
    connection = MagicMock()
    connection.execute.return_value = _FakeResult(one_row=_pallet_row())

    result = pallet_service.get_pallet_by_barcode(connection, "00001")

    assert result["barcode"] == "00001"
    assert result["expiration_date"] == "2027-07-01"
    assert result["brand_name"] == "Polly's Pop"


def test_get_pallet_by_barcode_raises_for_missing() -> None:
    connection = MagicMock()
    connection.execute.return_value = _FakeResult(one_row=None)

    with pytest.raises(PalletNotFoundError):
        pallet_service.get_pallet_by_barcode(connection, "00099")


def test_get_pallet_by_barcode_rejects_invalid_format() -> None:
    with pytest.raises(ValueError, match="invalid pallet barcode format"):
        pallet_service.get_pallet_by_barcode(MagicMock(), "abc")


def test_transfer_pallet_rejects_sold_pallet() -> None:
    connection = MagicMock()
    connection.execute.return_value = _FakeResult(
        one_row=_pallet_row(status="sold", sold_at=date.today())
    )

    with pytest.raises(PalletAlreadySoldError):
        pallet_service.transfer_pallet(
            connection,
            barcode="00001",
            to_location="Warehouse 1",
        )


def test_transfer_pallet_rejects_same_location() -> None:
    connection = MagicMock()
    connection.execute.return_value = _FakeResult(one_row=_pallet_row())

    with pytest.raises(InvalidTransferError, match="already at"):
        pallet_service.transfer_pallet(
            connection,
            barcode="00001",
            to_location="Production Floor",
        )


def test_create_pallet_raises_when_product_missing(monkeypatch) -> None:
    connection = MagicMock()
    connection.execute.return_value = _FakeResult(one_row=None)

    with pytest.raises(ProductNotFoundError):
        pallet_service.create_pallet(
            connection,
            product_id=999,
            bottled_at=date(2026, 7, 1),
            expiration_date=date(2027, 7, 1),
        )


def test_sell_pallet_raises_when_already_sold() -> None:
    connection = MagicMock()
    connection.execute.return_value = _FakeResult(
        one_row=_pallet_row(status="sold", sold_at=date.today())
    )

    with pytest.raises(PalletAlreadySoldError):
        pallet_service.sell_pallet(connection, barcode="00001")
