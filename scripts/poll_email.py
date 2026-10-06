"""Email poller: fetch card-use notifications and insert them as transactions.

Runs headless in GitHub Actions (see .github/workflows/email-ingest.yml).
Credentials come from environment variables:

    IMAP_HOST             Gmail: imap.gmail.com
    IMAP_USER             your Gmail address
    IMAP_APP_PASSWORD     Gmail app password (requires 2-Step Verification)
    SUPABASE_URL          Supabase project URL
    SUPABASE_SECRET_KEY   Supabase secret key

Usage:
    python scripts/poll_email.py              # normal run
    python scripts/poll_email.py --dry-run    # parse only, don't insert
"""

import argparse
import imaplib
import os
import socket
import sys

from src.core.database import create_transactions_bulk, get_categories
from src.core.email_ingest import IMAP_TIMEOUT_SECONDS, poll_and_normalize


def main() -> None:
    parser = argparse.ArgumentParser(description="Poll card-use notification emails")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and report only; do not insert into the database",
    )
    args = parser.parse_args()

    host = os.getenv("IMAP_HOST", "imap.gmail.com")
    user = os.getenv("IMAP_USER")
    password = os.getenv("IMAP_APP_PASSWORD")

    if not user or not password:
        print("ERROR: IMAP_USER and IMAP_APP_PASSWORD must be set", file=sys.stderr)
        sys.exit(1)

    print(f"Polling {host} as {user}...", flush=True)
    try:
        transactions, last_uid = poll_and_normalize(host, user, password)
    except imaplib.IMAP4.error as exc:
        # Gmail answers a bad password with '[AUTHENTICATIONFAILED] Invalid
        # credentials' in about a second. IMAP4.abort subclasses IMAP4.error,
        # so mid-session drops land here too.
        print(f"ERROR: IMAP request failed: {exc}", file=sys.stderr, flush=True)
        sys.exit(1)
    except (socket.timeout, TimeoutError) as exc:
        print(
            f"ERROR: IMAP timed out after {IMAP_TIMEOUT_SECONDS}s: {exc}",
            file=sys.stderr,
            flush=True,
        )
        sys.exit(1)
    print(f"Last UID: {last_uid}", flush=True)

    # Filter out transactions already in the database (idempotency)
    from datetime import timedelta

    from src.core.database import get_all_transactions
    from src.core.merging import merge_with_existing

    if transactions:
        dates = [t["date"] for t in transactions]
        existing = get_all_transactions(
            start_date=min(dates) - timedelta(days=3),
            end_date=max(dates) + timedelta(days=3),
        )
        transactions, skipped = merge_with_existing(transactions, existing)
        if skipped:
            print(f"Skipped {skipped} already tracked via statement")

    new_count = len(transactions)
    print(f"New transactions: {new_count}", flush=True)

    if args.dry_run:
        for t in transactions:
            print(
                f"  [dry-run] {t['date']} | {t['description'][:40]:40} | "
                f"{t['amount']:>12,.2f} {t['currency']} | {t['movement_type']}"
            )
        return

    if not transactions:
        print("Nothing to insert.")
        return

    # Map category names to IDs
    db_categories = get_categories()
    category_name_to_id = {c["name"]: c["id"] for c in db_categories}

    db_transactions = []
    for t in transactions:
        category_id = category_name_to_id.get(t.get("category_name", "Otros"))
        db_transactions.append(
            {
                "date": t["date"].isoformat(),
                "description": t["description"],
                "amount": t["amount"],
                "currency": t["currency"],
                "movement_type": t["movement_type"],
                "account": t["account"],
                "category_id": category_id,
                "metadata": t.get("metadata", {}),
                "source": "email",
            }
        )

    count = create_transactions_bulk(db_transactions)
    print(f"Inserted {count} transactions.")


if __name__ == "__main__":
    main()
