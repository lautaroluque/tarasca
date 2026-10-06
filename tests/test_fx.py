"""Tests for FX rates derived from the user's own converted swaps."""

from datetime import datetime

import pytest

from src.core.fx import (
    RateSample,
    build_rate_table,
    collect_rate_samples,
)

AS_OF = datetime(2026, 10, 6)


def test_collect_reads_executed_rate_from_conversion_metadata():
    rows = [
        {
            "date": "2026-09-01T12:00:00+00:00",
            "amount": 77516.5,
            "currency": "ARS",
            "metadata": {"monto_origen": 48.06, "moneda_origen": "USDT"},
        }
    ]
    samples = collect_rate_samples(rows)

    assert len(samples) == 1
    sample = samples[0]
    assert sample.source == "USDT"
    assert sample.target == "ARS"
    assert sample.target_per_source == pytest.approx(1613.0, rel=1e-3)
    assert sample.timestamp == datetime(2026, 9, 1, 12, 0)


def test_collect_skips_same_currency_and_metadata_free_rows():
    rows = [
        # Not a conversion: origin and target are the same currency
        {
            "date": "2026-09-18T00:00:00+00:00",
            "amount": -117409.21,
            "currency": "ARS",
            "metadata": {"monto_origen": 117409.21, "moneda_origen": "ARS"},
        },
        # Origin leg of a conversion: carries no executed rate
        {
            "date": "2026-09-18T00:00:00+00:00",
            "amount": -217.53,
            "currency": "USDT",
            "metadata": {"lado": "origen"},
        },
        # Plain movement
        {"date": "2026-09-18T00:00:00+00:00", "amount": -100.0, "currency": "ARS"},
    ]
    assert collect_rate_samples(rows) == []


def test_rate_table_prefers_recent_swaps_and_routes_through_pivot():
    samples = [
        RateSample("USDT", "ARS", datetime(2026, 1, 1), 1436.0),  # stale
        RateSample("USDT", "ARS", datetime(2026, 9, 1), 1613.0),
        RateSample("USDT", "ARS", datetime(2026, 10, 1), 1614.0),
        # No direct ARS/USD swap: USD only ever trades against USDT
        RateSample("USDT", "USD", datetime(2026, 9, 15), 1.034),
    ]

    rates = build_rate_table(samples, as_of=AS_OF, lookback_days=60)

    assert rates.ars_per_unit["ARS"] == 1.0
    assert rates.ars_per_unit["USDT"] == pytest.approx(1613.5)
    assert rates.ars_per_unit["USD"] == pytest.approx(1613.5 / 1.034)
    assert rates.sample_counts["USDT"] == 2  # the stale swap is not counted
    assert rates.newest_sample["USDT"] == datetime(2026, 10, 1)
    # Cross conversion through the pivot: 1 USDT = 1.034 USD → 1 USD = 1/1.034 USDT
    assert rates.convert(1.0, "USD", "USDT") == pytest.approx(1 / 1.034)


def test_rate_table_falls_back_to_stale_swaps_when_there_is_nothing_recent():
    samples = [RateSample("USDT", "ARS", datetime(2026, 1, 1), 1436.0)]

    rates = build_rate_table(samples, as_of=AS_OF, lookback_days=60)

    assert rates.ars_per_unit["USDT"] == pytest.approx(1436.0)
    assert rates.sample_counts["USDT"] == 1


def test_unreachable_currency_has_no_rate():
    rates = build_rate_table(
        [RateSample("USDT", "ARS", datetime(2026, 9, 1), 1600.0)], as_of=AS_OF
    )

    assert rates.has_rate("ARS")
    assert not rates.has_rate("USD")
    with pytest.raises(KeyError):
        rates.convert(1.0, "USD", "ARS")
