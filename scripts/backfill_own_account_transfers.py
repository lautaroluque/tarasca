"""Reclassify own-account transfers that were imported as expenses.

"Retiro a una cuenta propia" (money moved to another of my own accounts)
used to match the ``retiro a`` rule — written for withdrawals to a person —
and was stored as ``gasto``, so own-account transfers inflated every expense
metric (in the current data: 63% of ARS "gastos" and 96% of USD "gastos").

``src/core/movements.py`` is already fixed for future imports; this script
applies the same correction to rows already in the database. Only
``movement_type`` changes — amounts, dates and categories are untouched —
so balances are unaffected while expense metrics stop counting money that
merely moved.

Usage (credentials via environment, same as scripts/poll_email.py):

    uv run python scripts/backfill_own_account_transfers.py                 # dry run
    uv run python scripts/backfill_own_account_transfers.py --apply        # write + rollback file
    uv run python scripts/backfill_own_account_transfers.py --rollback FILE
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.core.database import get_supabase_client

# Matches both "Retiro a una cuenta propia" and "Depósito de cuenta propia".
OWN_ACCOUNT_PATTERN = re.compile(r"cuenta propia", re.IGNORECASE)

# Rows per UPDATE statement (Supabase caps request bodies comfortably above
# this; kept small so a partial failure is easy to inspect).
BATCH_SIZE = 200

DEFAULT_ROLLBACK_PATH = Path("backfill_own_account_rollback.json")


def _fetch_rows(client: Any, movement_type: str) -> list[dict[str, Any]]:
    """All rows of one movement type, paged past Supabase's 1000-row cap."""
    rows: list[dict[str, Any]] = []
    skip = 0
    while True:
        page = (
            client.table("transactions")
            .select("id,account,date,amount,currency,description,movement_type")
            .eq("movement_type", movement_type)
            .order("date", desc=True)
            .range(skip, skip + 999)
            .execute()
            .data
        )
        rows.extend(page)
        if len(page) < 1000:
            return rows
        skip += 1000


def _report(matches: list[dict[str, Any]]) -> None:
    buckets: dict[tuple[str, str], dict[str, float]] = {}
    for row in matches:
        bucket = buckets.setdefault(
            (row["account"], row["currency"]), {"count": 0, "amount": 0.0}
        )
        bucket["count"] += 1
        bucket["amount"] += float(row["amount"])

    print(f"Rows reclassified as transferencia: {len(matches)}")
    for (account, currency), stats in sorted(buckets.items()):
        print(
            f"  {account} · {currency}: {int(stats['count'])} rows, "
            f"{stats['amount']:,.2f} {currency} (no longer counted as spending)"
        )


def _apply(matches: list[dict[str, Any]], rollback_path: Path) -> None:
    client = get_supabase_client()
    for start in range(0, len(matches), BATCH_SIZE):
        batch = matches[start : start + BATCH_SIZE]
        (
            client.table("transactions")
            .update({"movement_type": "transferencia"})
            .in_("id", [row["id"] for row in batch])
            .execute()
        )

    rollback_path.write_text(
        json.dumps(
            {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "reason": "own-account transfers stored as gasto",
                "rows": [
                    {"id": row["id"], "movement_type": row["movement_type"]}
                    for row in matches
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Updated {len(matches)} rows.")
    print(f"Rollback file: {rollback_path}")


def _rollback(rollback_path: Path) -> None:
    payload = json.loads(rollback_path.read_text(encoding="utf-8"))
    rows = payload.get("rows", [])
    client = get_supabase_client()
    updated = 0
    for start in range(0, len(rows), BATCH_SIZE):
        batch = rows[start : start + BATCH_SIZE]
        response = (
            client.table("transactions")
            .update({"movement_type": batch[0]["movement_type"]})
            .in_("id", [row["id"] for row in batch])
            .execute()
        )
        updated += len(response.data)
    print(f"Restored movement_type on {updated} rows.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write the changes (default is a dry run that only reports).",
    )
    parser.add_argument(
        "--rollback",
        type=Path,
        metavar="FILE",
        help="Restore movement_type from a rollback file written by --apply.",
    )
    parser.add_argument(
        "--rollback-file",
        type=Path,
        default=DEFAULT_ROLLBACK_PATH,
        help=f"Where --apply writes its rollback file (default: {DEFAULT_ROLLBACK_PATH}).",
    )
    args = parser.parse_args()

    if args.rollback:
        if not args.rollback.exists():
            print(f"Rollback file not found: {args.rollback}", file=sys.stderr)
            return 1
        _rollback(args.rollback)
        return 0

    client = get_supabase_client()
    matches = [
        row
        for row in _fetch_rows(client, "gasto")
        if OWN_ACCOUNT_PATTERN.search(row["description"] or "")
    ]
    _report(matches)

    if not matches:
        return 0
    if not args.apply:
        print("Dry run: nothing written. Re-run with --apply to update.")
        return 0

    _apply(matches, args.rollback_file)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
