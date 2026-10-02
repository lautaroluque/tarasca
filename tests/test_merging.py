"""Tests for cross-source merge logic (email ↔ statement dedupe)."""

from datetime import datetime

from src.core.merging import find_cross_source_match, merge_with_existing


def make_row(
    description: str,
    amount: float,
    currency: str = "ARS",
    account: str = "Galicia Mastercard",
    date: datetime | None = None,
) -> dict:
    return {
        "date": date or datetime(2026, 10, 2, 13, 36),
        "description": description,
        "amount": amount,
        "currency": currency,
        "account": account,
    }


def test_match_same_merchant_same_amount():
    candidate = make_row("PEDIDOSYA*NOA EMPANADA", -38710.00)
    existing = [make_row("PEDIDOSYA*NOA EMPANADA", -38710.00)]
    assert find_cross_source_match(candidate, existing) == 0


def test_match_email_time_vs_statement_midnight():
    # Email has time, statement has midnight — same calendar day
    candidate = make_row("PEDIDOSYA*NOA EMPANADA", -38710.00,
                         date=datetime(2026, 10, 2, 13, 36))
    existing = [make_row("PEDIDOSYA*NOA EMPANADA", -38710.00,
                         date=datetime(2026, 10, 2, 0, 0))]
    assert find_cross_source_match(candidate, existing) == 0


def test_match_within_3_day_window():
    candidate = make_row("PEDIDOSYA*NOA EMPANADA", -38710.00,
                         date=datetime(2026, 10, 5, 10, 0))
    existing = [make_row("PEDIDOSYA*NOA EMPANADA", -38710.00,
                         date=datetime(2026, 10, 2, 10, 0))]
    assert find_cross_source_match(candidate, existing) == 0


def test_no_match_outside_3_day_window():
    candidate = make_row("PEDIDOSYA*NOA EMPANADA", -38710.00,
                         date=datetime(2026, 10, 10, 10, 0))
    existing = [make_row("PEDIDOSYA*NOA EMPANADA", -38710.00,
                         date=datetime(2026, 10, 2, 10, 0))]
    assert find_cross_source_match(candidate, existing) is None


def test_no_match_different_amount():
    candidate = make_row("PEDIDOSYA*NOA EMPANADA", -38710.00)
    existing = [make_row("PEDIDOSYA*NOA EMPANADA", -100.00)]
    assert find_cross_source_match(candidate, existing) is None


def test_no_match_different_merchant_same_amount():
    # Token guard: different merchants with the same amount must not match
    candidate = make_row("CARREFOUR ROSARIO", -38710.00)
    existing = [make_row("PEDIDOSYA*NOA EMPANADA", -38710.00)]
    assert find_cross_source_match(candidate, existing) is None


def test_no_match_different_currency():
    candidate = make_row("PEDIDOSYA*NOA EMPANADA", -38710.00, currency="USD")
    existing = [make_row("PEDIDOSYA*NOA EMPANADA", -38710.00, currency="ARS")]
    assert find_cross_source_match(candidate, existing) is None


def test_no_match_different_account():
    candidate = make_row("PEDIDOSYA*NOA EMPANADA", -38710.00, account="Fiwind")
    existing = [make_row("PEDIDOSYA*NOA EMPANADA", -38710.00,
                         account="Galicia Mastercard")]
    assert find_cross_source_match(candidate, existing) is None


def test_count_based_pairing_equal_amounts():
    # Two identical purchases: each email row matches its own statement row
    candidate1 = make_row("PEDIDOSYA*NOA EMPANADA", -38710.00,
                          date=datetime(2026, 10, 2, 12, 51))
    candidate2 = make_row("PEDIDOSYA*NOA EMPANADA", -38710.00,
                          date=datetime(2026, 10, 2, 13, 36))
    existing = [
        make_row("PEDIDOSYA*NOA EMPANADA", -38710.00,
                 date=datetime(2026, 10, 2, 0, 0)),
        make_row("PEDIDOSYA*NOA EMPANADA", -38710.00,
                 date=datetime(2026, 10, 2, 0, 0)),
    ]
    to_insert, skipped = merge_with_existing([candidate1, candidate2], existing)
    assert skipped == 2
    assert to_insert == []


def test_merge_with_existing_skips_matched():
    candidate = make_row("PEDIDOSYA*NOA EMPANADA", -38710.00)
    existing = [make_row("PEDIDOSYA*NOA EMPANADA", -38710.00)]
    to_insert, skipped = merge_with_existing([candidate], existing)
    assert skipped == 1
    assert to_insert == []


def test_merge_with_existing_keeps_unmatched():
    candidate = make_row("NEW*PURCHASE", -500.00)
    existing = [make_row("PEDIDOSYA*NOA EMPANADA", -38710.00)]
    to_insert, skipped = merge_with_existing([candidate], existing)
    assert skipped == 0
    assert len(to_insert) == 1
