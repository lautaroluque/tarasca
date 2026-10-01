"""Inspect PDF word positions to design the positional parser."""

import pdfplumber

with pdfplumber.open(r"samples\galicia-mastercard\Resumen .pdf") as pdf:
    for pageno, page in enumerate(pdf.pages[:2], start=1):
        print(f"{'=' * 70}\nPAGE {pageno}\n{'=' * 70}")
        words = page.extract_words()
        # Cluster words into lines by vertical position
        lines = {}
        for w in words:
            key = round(w["top"] / 3)
            lines.setdefault(key, []).append(w)
        for key in sorted(lines):
            ws = sorted(lines[key], key=lambda w: w["x0"])
            text = " ".join(f"[{w['text']}@{int(w['x0'])}]" for w in ws)
            print(f"y={int(ws[0]['top']):3d} {text}")
