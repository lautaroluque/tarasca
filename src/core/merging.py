"""Cross-source merge: prevent duplicates between email and statement rows.

A card-use notification (email) and the same purchase in the monthly
statement (extracto) describe the same transaction but with different
descriptions, timestamps, and no shared comprobante. This module matches
them so the second one imported is skipped.

Match signature: (account, currency, |amount|) + calendar date within ±3 days
+ description token overlap. Count-based pairing: each existing row can only
match one incoming row (handles repeated equal amounts correctly).
"""

import re
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

ARGENTINA_TZ = ZoneInfo("America/Argentina/Buenos_Aires")

# Tokens shorter than this are ignored (too generic: "su", "la", "00"...)
MIN_TOKEN_LENGTH = 4

# How many calendar days apart two rows can be and still match
DATE_TOLERANCE_DAYS = 3


def _normalize_date(value: Any) -> date:
    """Convert a datetime or ISO string to a naive Argentina-local date."""
    dt: datetime
    if isinstance(value, str):
        dt = datetime.fromisoformat(value)
    elif isinstance(value, datetime):
        dt = value
    else:
        raise ValueError(f"Expected datetime or ISO string, got {type(value)}")
    if dt.tzinfo is not None:
        dt = dt.astimezone(ARGENTINA_TZ).replace(tzinfo=None)
    return dt.date()


def _tokens(description: str) -> set[str]:
    """Extract significant lowercase tokens from a description."""
    return {
        t
        for t in re.findall(r"[a-záéíóúñü0-9]+", description.lower())
        if len(t) >= MIN_TOKEN_LENGTH
    }


def find_cross_source_match(
    candidate: dict[str, Any],
    existing_rows: list[dict[str, Any]],
    consumed: set[int] | None = None,
) -> int | None:
    """Return the index of an existing row matching candidate, or None.

    Args:
        candidate: The incoming transaction dict.
        existing_rows: Rows already in the database.
        consumed: Indices of existing rows already matched (count-based pairing).
    """
    if consumed is None:
        consumed = set()

    cand_date = _normalize_date(candidate["date"])
    cand_amount = round(abs(float(candidate["amount"])), 2)
    cand_currency = candidate["currency"]
    cand_account = candidate.get("account", "")
    cand_tokens = _tokens(candidate["description"])

    for i, row in enumerate(existing_rows):
        if i in consumed:
            continue
        if row.get("account", "") != cand_account:
            continue
        if row["currency"] != cand_currency:
            continue
        if round(abs(float(row["amount"])), 2) != cand_amount:
            continue
        row_date = _normalize_date(row["date"])
        if abs((row_date - cand_date).days) > DATE_TOLERANCE_DAYS:
            continue
        # Token guard: descriptions must share at least one significant token
        if not (cand_tokens & _tokens(row["description"])):
            continue
        return i

    return None


def merge_with_existing(
    new_rows: list[dict[str, Any]],
    existing_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    """Split new_rows into (to_insert, merged_skipped_count).

    A new row is skipped when it matches an existing row (cross-source).
    Count-based: each existing row can only match one new row.
    """
    consumed: set[int] = set()
    to_insert: list[dict[str, Any]] = []
    skipped = 0

    for row in new_rows:
        match_idx = find_cross_source_match(row, existing_rows, consumed)
        if match_idx is not None:
            consumed.add(match_idx)
            skipped += 1
        else:
            to_insert.append(row)

    return to_insert, skipped
