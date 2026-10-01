"""Clean up rows imported by the broken parser and backfill missing rows.

Compares every row in the transactions table against what the current parser
produces from the two sample files, then:

  1. deletes rows that don't match (legacy duplicates, phantom USD rows,
     wrong signs) -- they all come from imports made with the old parser;
  2. inserts expected rows that are missing from the table.

Dry run by default; pass --yes to execute.

Usage: uv run python scripts/cleanup_imports.py [--yes]
"""

import argparse
import tomllib
from datetime import timezone
from pathlib import Path

from supabase import Client, create_client

from src.core.categorization import categorize_transaction, get_default_categories
from src.core.ingestion import parse_file

SAMPLES = [
    (
        Path(r"samples\galicia-mastercard\Resumen .pdf"),
        "galicia_mastercard",
        ".pdf",
        "Galicia Mastercard",
    ),
    (
        Path(r"samples\fiwind\Actividad_Fiwind_01-10-2026_31-10-2026.xlsx"),
        "fiwind",
        ".xlsx",
        "Fiwind",
    ),
]


def dedupe_key(row: dict) -> tuple:
    """Same identity key used by the app's import dedupe."""
    from datetime import datetime

    date = row["date"]
    if isinstance(date, str):
        date = datetime.fromisoformat(date)
    if date.tzinfo is not None:
        date = date.astimezone(timezone.utc).replace(tzinfo=None)

    metadata = row.get("metadata") or {}
    return (
        date,
        row["description"],
        round(float(row["amount"]), 2),
        row["currency"],
        row.get("account", ""),
        metadata.get("comprobante", ""),
    )


def get_client() -> Client:
    with open(".streamlit/secrets.toml", "rb") as f:
        secrets = tomllib.load(f)
    supa = secrets["supabase"]
    return create_client(supa["url"], supa["secret_key"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--yes", action="store_true", help="execute the cleanup")
    args = parser.parse_args()

    client = get_client()

    # What the current parser produces for both samples
    expected: dict[tuple, dict] = {}
    for path, template_name, ext, account in SAMPLES:
        for t in parse_file(path.read_bytes(), template_name, ext):
            t["account"] = account
            expected[dedupe_key(t)] = t

    rows = client.table("transactions").select("*").execute().data
    existing_keys = {dedupe_key(r) for r in rows}

    legacy = [r for r in rows if dedupe_key(r) not in expected]
    missing = [t for k, t in expected.items() if k not in existing_keys]

    print(f"DB rows: {len(rows)}")
    print(f"Current parser expects: {len(expected)}")
    print(f"Legacy rows to delete: {len(legacy)}")
    print(f"Missing rows to insert: {len(missing)}")

    by_account: dict[str, int] = {}
    for r in legacy:
        by_account[r["account"]] = by_account.get(r["account"], 0) + 1
    for account, count in sorted(by_account.items()):
        print(f"  legacy in {account}: {count}")

    for t in missing:
        print(
            f"  missing: {t['date']} | {t['description'][:34]:34} | "
            f"{t['amount']:>12,.2f} {t['currency']} ({t['movement_type']})"
        )

    if not args.yes:
        print("\nDry run only. Re-run with --yes to apply.")
        return

    # 1. Delete legacy rows (chunked)
    for i in range(0, len(legacy), 100):
        ids = [r["id"] for r in legacy[i : i + 100]]
        client.table("transactions").delete().in_("id", ids).execute()
    print(f"Deleted {len(legacy)} legacy rows")

    # 2. Backfill missing rows with category assignment
    if missing:
        categories = client.table("categories").select("*").execute().data
        name_to_id = {c["name"]: c["id"] for c in categories}
        keyword_categories = get_default_categories()

        payload = []
        for t in missing:
            category_name = categorize_transaction(t["description"], keyword_categories)
            payload.append(
                {
                    "date": t["date"].isoformat(),
                    "description": t["description"],
                    "amount": t["amount"],
                    "currency": t["currency"],
                    "movement_type": t["movement_type"],
                    "account": t["account"],
                    "category_id": name_to_id.get(category_name or "Otros"),
                    "metadata": t.get("metadata", {}),
                }
            )
        client.table("transactions").insert(payload).execute()
        print(f"Inserted {len(payload)} missing rows")

    final = (
        client.table("transactions").select("*", count="exact").execute()
    )
    print(f"Done. transactions now has {final.count} rows (expected {len(expected)})")


if __name__ == "__main__":
    main()
