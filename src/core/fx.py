"""Exchange rates derived from the user's own imported swaps.

Combining ARS, USD and USDT into a single figure needs a conversion rate.
Rather than calling an external rate API, rates are read from the
conversions already imported from statements: every swap leg stores the
executed trade (``metadata.monto_origen`` / ``metadata.moneda_origen`` of
what was spent, against ``amount`` / ``currency`` of what was received), so
the numbers come from trades the user actually made — offline, no API key,
and consistent with how the money really moved.

Rates are kept as an "ARS per 1 unit" table (ARS is the pivot because it is
the only currency every swap touches) and medianed over recent samples so a
single stale or outlier swap cannot skew the total.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from statistics import median
from typing import Any, Iterable

# Pivot currency of the rate table: ARS per 1 unit of each currency.
PIVOT_CURRENCY = "ARS"

# How far back a sample counts as "current" before the table falls back to
# older data for that currency (a currency with no recent swap at all still
# gets a rate, just a stale one).
DEFAULT_LOOKBACK_DAYS = 60


@dataclass(frozen=True)
class RateSample:
    """One executed conversion: 1 ``source`` = ``target_per_source`` ``target``."""

    source: str
    target: str
    timestamp: datetime | None
    target_per_source: float


@dataclass(frozen=True)
class RateTable:
    """ARS-based rates plus enough provenance to explain them in the UI."""

    ars_per_unit: dict[str, float]
    sample_counts: dict[str, int]
    newest_sample: dict[str, datetime | None]

    def has_rate(self, currency: str) -> bool:
        return currency in self.ars_per_unit

    def convert(self, amount: float, source: str, target: str) -> float:
        """Convert ``amount`` from ``source`` into ``target``."""
        source_rate = self.ars_per_unit.get(source)
        target_rate = self.ars_per_unit.get(target)
        if source_rate is None or target_rate is None:
            missing = source if source_rate is None else target
            raise KeyError(f"No exchange rate for {missing}")
        return amount * source_rate / target_rate


def collect_rate_samples(rows: Iterable[dict[str, Any]]) -> list[RateSample]:
    """Extract conversion rates from transaction rows.

    Only rows carrying conversion metadata (``moneda_origen`` + a positive
    ``monto_origen``) are considered; same-currency bookkeeping rows such as
    ``{"moneda_origen": "ARS", "currency": "ARS"}`` describe no exchange and
    are skipped.
    """
    samples: list[RateSample] = []
    for row in rows:
        metadata = row.get("metadata") or {}
        source = metadata.get("moneda_origen")
        origin_amount = metadata.get("monto_origen")
        target = row.get("currency")
        if not source or not target or origin_amount is None or source == target:
            continue
        try:
            units_source = float(origin_amount)
            units_target = abs(float(row["amount"]))
        except (KeyError, TypeError, ValueError):
            continue
        if units_source <= 0 or units_target <= 0:
            continue
        samples.append(
            RateSample(
                source=str(source).upper(),
                target=str(target).upper(),
                timestamp=_parse_timestamp(row.get("date")),
                target_per_source=units_target / units_source,
            )
        )
    return samples


def build_rate_table(
    samples: Iterable[RateSample],
    *,
    as_of: datetime | None = None,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
) -> RateTable:
    """Build an ARS-based rate table from executed swaps.

    Currencies are valued in breadth-first order from the pivot, preferring
    samples inside ``lookback_days`` and falling back to older ones for any
    currency that has no recent swap (e.g. USD, converted only once in a
    while).
    """
    samples = list(samples)
    as_of = as_of or datetime.now(timezone.utc).replace(tzinfo=None)
    cutoff = as_of - timedelta(days=lookback_days)
    recent = [s for s in samples if s.timestamp is not None and s.timestamp >= cutoff]

    ars_per_unit = {PIVOT_CURRENCY: 1.0}
    sample_counts = {PIVOT_CURRENCY: 0}
    newest_sample: dict[str, datetime | None] = {PIVOT_CURRENCY: None}

    for currency in _reachable_currencies(samples):
        if currency in ars_per_unit:
            continue
        value = _median_rate(recent, currency, ars_per_unit)
        used = recent
        if value is None:
            value = _median_rate(samples, currency, ars_per_unit)
            used = samples
        if value is None:
            # Not reachable from the pivot yet; a later currency may anchor it.
            continue
        ars_per_unit[currency] = value
        sample_counts[currency] = len(_samples_for(used, currency, ars_per_unit))
        newest_sample[currency] = max(
            (s.timestamp for s in _samples_for(used, currency, ars_per_unit) if s.timestamp),
            default=None,
        )

    return RateTable(
        ars_per_unit=ars_per_unit,
        sample_counts=sample_counts,
        newest_sample=newest_sample,
    )


def _reachable_currencies(samples: list[RateSample]) -> list[str]:
    """Currencies connected to the pivot, nearest first."""
    adjacency: dict[str, set[str]] = {}
    for sample in samples:
        adjacency.setdefault(sample.source, set()).add(sample.target)
        adjacency.setdefault(sample.target, set()).add(sample.source)

    order: list[str] = []
    seen = {PIVOT_CURRENCY}
    frontier = [PIVOT_CURRENCY]
    while frontier:
        next_frontier: list[str] = []
        for node in frontier:
            for neighbour in sorted(adjacency.get(node, ())):
                if neighbour not in seen:
                    seen.add(neighbour)
                    order.append(neighbour)
                    next_frontier.append(neighbour)
        frontier = next_frontier
    return order


def _samples_for(
    samples: list[RateSample], currency: str, ars_per_unit: dict[str, float]
) -> list[RateSample]:
    """Samples that convert ``currency`` against an already-valued currency."""
    return [
        s
        for s in samples
        if (s.target == currency and s.source in ars_per_unit)
        or (s.source == currency and s.target in ars_per_unit)
    ]


def _median_rate(
    samples: list[RateSample], currency: str, ars_per_unit: dict[str, float]
) -> float | None:
    """Median ARS-per-unit rate implied by ``samples``."""
    candidates: list[float] = []
    for sample in _samples_for(samples, currency, ars_per_unit):
        if sample.target == currency:
            candidates.append(ars_per_unit[sample.source] / sample.target_per_source)
        else:
            candidates.append(ars_per_unit[sample.target] * sample.target_per_source)
    if not candidates:
        return None
    return median(candidates)


def _parse_timestamp(value: Any) -> datetime | None:
    """Parse a Supabase ISO timestamp into naive UTC, or None if unusable."""
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed
