"""Diagnostic script: parse sample files and inspect results."""

from collections import Counter

from src.core.ingestion import parse_file

print("=" * 70)
print("GALICIA MASTERCARD (PDF)")
print("=" * 70)

with open(r"samples\galicia-mastercard\Resumen .pdf", "rb") as f:
    pdf_data = f.read()

txs = parse_file(pdf_data, "galicia_mastercard", "pdf")
print(f"Total transactions: {len(txs)}")

keys = [
    (
        t["date"],
        t["description"],
        t["amount"],
        t["currency"],
        t["metadata"].get("comprobante"),
    )
    for t in txs
]
dupes = [k for k, c in Counter(keys).items() if c > 1]
print(f"Exact duplicates (incl. comprobante): {len(dupes)}")
for d in dupes[:10]:
    print(f"  DUP: {d}")

print(f"\nMovement types: {Counter(t['movement_type'] for t in txs)}")
for t in txs:
    if t["movement_type"] in ("ingreso", "transferencia"):
        print(
            f"  {t['date']} | {t['description'][:40]:40} | {t['amount']:>14,.2f} "
            f"| {t['currency']} | {t['movement_type']}"
        )

print("\nFirst 15 transactions:")
for t in txs[:15]:
    print(
        f"  {t['date']} | {t['description'][:40]:40} | {t['amount']:>14,.2f} "
        f"| {t['currency']} | {t['movement_type']:14} | {t['metadata']}"
    )

print("\n" + "=" * 70)
print("FIWIND (EXCEL)")
print("=" * 70)

with open(r"samples\fiwind\Actividad_Fiwind_01-10-2026_31-10-2026.xlsx", "rb") as f:
    xls_data = f.read()

txs2 = parse_file(xls_data, "fiwind", "xlsx")
print(f"Total transactions: {len(txs2)}")
print(f"Currencies: {Counter(t['currency'] for t in txs2)}")
for t in txs2:
    print(
        f"  {t['date']} | {t['description'][:40]:40} | {t['amount']:>14,.2f} "
        f"| {t['currency']} | {t['movement_type']:14} | {t['metadata']}"
    )
