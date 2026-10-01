"""Tests for the upload page import helpers."""

from datetime import datetime

from src.pages.upload import _dedupe_key


def _parsed_row(**overrides) -> dict:
    """Row as produced by the parsers (naive datetime, metadata dict)."""
    row = {
        "date": datetime(2026, 9, 1, 0, 0, 0),
        "description": "SU PAGO",
        "amount": 1233608.29,
        "currency": "ARS",
        "account": "Galicia Mastercard",
        "metadata": {"comprobante": "00192", "seccion": "detalle"},
    }
    row.update(overrides)
    return row


def _db_row(**overrides) -> dict:
    """Row as returned by Supabase (ISO date string, possibly offset-aware)."""
    row = {
        "date": "2026-09-01T00:00:00+00:00",
        "description": "SU PAGO",
        "amount": 1233608.29,
        "currency": "ARS",
        "account": "Galicia Mastercard",
        "metadata": {"comprobante": "00192", "seccion": "detalle"},
    }
    row.update(overrides)
    return row


def test_dedupe_key_matches_across_representations():
    """A parsed row and its database representation share the same key."""
    assert _dedupe_key(_parsed_row()) == _dedupe_key(_db_row())


def test_dedupe_key_naive_iso_string():
    assert _dedupe_key(_parsed_row()) == _dedupe_key(_db_row(date="2026-09-01T00:00:00"))


def test_dedupe_key_differs_by_comprobante():
    """Same merchant/day/amount but different comprobante = distinct rows."""
    parsed = _parsed_row()
    other = _db_row(metadata={"comprobante": "00193", "seccion": "detalle"})
    assert _dedupe_key(parsed) != _dedupe_key(other)


def test_dedupe_key_differs_by_amount_and_currency():
    assert _dedupe_key(_parsed_row()) != _dedupe_key(_db_row(amount=-34100.0))
    assert _dedupe_key(_parsed_row()) != _dedupe_key(_db_row(currency="USD"))


def test_dedupe_key_missing_metadata():
    """Rows without metadata (e.g. Fiwind) still produce a stable key."""
    parsed = _parsed_row(metadata={})
    db = _db_row(metadata=None)
    assert _dedupe_key(parsed) == _dedupe_key(db)
