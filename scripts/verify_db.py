"""Read-only verification after cleanup."""

import tomllib
from collections import Counter

from supabase import create_client

s = tomllib.load(open(".streamlit/secrets.toml", "rb"))["supabase"]
c = create_client(s["url"], s["secret_key"])

rows = c.table("transactions").select("*").execute().data
print(f"Total rows: {len(rows)}")
print(f"By account: {dict(Counter(r['account'] for r in rows))}")
for account in sorted({r["account"] for r in rows}):
    subset = [r for r in rows if r["account"] == account]
    print(f"\n{account}: {len(subset)} rows")
    print(f"  movement_type: {dict(Counter(r['movement_type'] for r in subset))}")
    print(f"  currency: {dict(Counter(r['currency'] for r in subset))}")
    dates = sorted(r["date"] for r in subset)
    print(f"  range: {dates[0][:10]} .. {dates[-1][:10]}")

# No duplicate (date, description, currency, comprobante) tuples
keys = [
    (
        r["date"],
        r["description"],
        r["currency"],
        (r.get("metadata") or {}).get("comprobante"),
    )
    for r in rows
]
dupes = [k for k, n in Counter(keys).items() if n > 1]
print(f"\nDuplicate keys: {len(dupes)}")
for d in dupes:
    print(f"  {d}")

# Signs sanity: gastos negative, ingresos positive
bad = [
    r
    for r in rows
    if (r["movement_type"] == "gasto" and r["amount"] > 0)
    or (r["movement_type"] == "ingreso" and r["amount"] < 0)
]
print(f"Sign inconsistencies: {len(bad)}")
for r in bad:
    print(f"  {r['description']} {r['amount']}")
