"""File parsing and ingestion logic."""

import io
import re
from datetime import datetime
from typing import Any

import pandas as pd
import pdfplumber

from src.core.movements import classify_movement
from src.core.templates import BankTemplate, get_template

# Spanish month abbreviations (statements are never locale-independent)
_MONTHS_ES = {
    "ene": 1,
    "feb": 2,
    "mar": 3,
    "abr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "ago": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dic": 12,
}

_DATE_WORD_RE = re.compile(r"^(\d{2})-([A-Za-z]{3})-(\d{2})$")
_AMOUNT_WORD_RE = re.compile(r"^-?\d+(?:\.\d{3})*,\d{2}$")
_COMPROBANTE_RE = re.compile(r"^\d{5}$")


def parse_amount_argentine(amount_str: str) -> float:
    """Parse Argentine format number (1.234,56) to float."""
    if pd.isna(amount_str) or amount_str == "":
        return 0.0

    # Remove currency symbols and whitespace
    amount_str = str(amount_str).strip().replace("$", "").replace(" ", "")

    # Argentine format: dots for thousands, comma for decimals
    # Remove dots (thousands separator) and replace comma with dot (decimal)
    amount_str = amount_str.replace(".", "").replace(",", ".")

    try:
        return float(amount_str)
    except ValueError:
        return 0.0


def parse_spanish_date(text: str) -> datetime | None:
    """Parse a DD-Mon-YY word with Spanish month abbreviations (Ago, Dic...)."""
    match = _DATE_WORD_RE.fullmatch(text.strip())
    if not match:
        return None
    month = _MONTHS_ES.get(match.group(2).lower())
    if month is None:
        return None
    day, year = int(match.group(1)), int(match.group(3))
    try:
        return datetime(2000 + year, month, day)
    except ValueError:
        return None


def _parse_rows_from_df(df: pd.DataFrame, template: BankTemplate) -> list[dict[str, Any]]:
    """Parse a tabular DataFrame (Excel/CSV) using template column mapping."""
    transactions = []
    for _, row in df.iterrows():
        # Parse date
        date_val = row.get(template.column_mapping.get("date", ""))
        if pd.isna(date_val):
            continue

        if isinstance(date_val, str):
            date = datetime.strptime(date_val, template.date_format or "%d/%m/%Y")
        else:
            date = pd.to_datetime(date_val).to_pydatetime()

        # Parse amount
        amount = row.get(template.column_mapping.get("amount", ""), 0)
        if isinstance(amount, str):
            amount = parse_amount_argentine(amount)
        else:
            amount = float(amount) if not pd.isna(amount) else 0.0

        # Parse currency
        currency = str(row.get(template.column_mapping.get("currency", ""), "ARS"))
        if pd.isna(currency) or currency == "":
            currency = "ARS"

        # Parse description
        description = str(row.get(template.column_mapping.get("description", ""), ""))
        if pd.isna(description):
            description = ""

        # Extract metadata
        metadata = {}
        for meta_field, col_name in template.metadata_fields.items():
            if col_name in df.columns:
                val = row.get(col_name)
                if not pd.isna(val):
                    metadata[meta_field] = val

        transactions.append(
            {
                "date": date,
                "description": description,
                "amount": amount,
                "currency": currency,
                "account": template.name,
                "metadata": metadata,
            }
        )

        # Currency conversions move money between the account's own balances:
        # emit the opposite side too so per-currency balances stay consistent.
        # "Monto Origen" is the currency being spent, "Monto" the one received.
        orig_amount = metadata.get("monto_origen")
        orig_currency = metadata.get("moneda_origen")
        if orig_amount is not None and orig_currency and str(orig_currency) != currency:
            transactions.append(
                {
                    "date": date,
                    "description": description,
                    "amount": float(orig_amount),
                    "currency": str(orig_currency),
                    "account": template.name,
                    "metadata": {"tipo": metadata.get("tipo", ""), "lado": "origen"},
                    "movement_type_hint": ("transferencia", "out"),
                }
            )

    return transactions


def parse_excel(file_content: bytes, template: BankTemplate) -> list[dict[str, Any]]:
    """Parse Excel file using template."""
    df = pd.read_excel(io.BytesIO(file_content), sheet_name=template.sheet_name)
    return _parse_rows_from_df(df, template)


def parse_csv(file_content: bytes, template: BankTemplate) -> list[dict[str, Any]]:
    """Parse CSV file using template."""
    df = pd.read_csv(io.BytesIO(file_content))
    return _parse_rows_from_df(df, template)


def parse_pdf(file_content: bytes, template: BankTemplate) -> list[dict[str, Any]]:
    """Parse a bank statement PDF using word positions.

    Column values are assigned by horizontal position (x-coordinate) relative
    to the PESOS/DOLARES header words, so amounts inside the description text
    are never mistaken for statement amounts.
    """
    transactions: list[dict[str, Any]] = []

    with pdfplumber.open(io.BytesIO(file_content)) as pdf:
        for page in pdf.pages:
            words = page.extract_words()
            if not words:
                continue
            transactions.extend(_parse_pdf_page(words, template))

    return transactions


def _cluster_lines(
    words: list[dict[str, Any]], tolerance: float = 2.5
) -> list[list[dict[str, Any]]]:
    """Group words into visual lines by vertical position."""
    lines: list[list[dict[str, Any]]] = []
    for word in sorted(words, key=lambda w: (w["top"], w["x0"])):
        if lines and abs(word["top"] - lines[-1][0]["top"]) <= tolerance:
            lines[-1].append(word)
        else:
            lines.append([word])
    return lines


def _parse_pdf_page(
    words: list[dict[str, Any]], template: BankTemplate
) -> list[dict[str, Any]]:
    """Parse one PDF page: header lines set columns, date lines become rows."""
    rows: list[dict[str, Any]] = []
    current_section = ""
    pesos_x0: float | None = None
    boundary: float | None = None

    for line in _cluster_lines(words):
        ws = sorted(line, key=lambda w: w["x0"])
        texts = [w["text"] for w in ws]
        upper = [t.upper() for t in texts]

        # Column header: "... PESOS DOLARES ..." -> record column x-positions.
        # The word right after PESOS is the USD header (may have bad encoding).
        idx = upper.index("PESOS") if "PESOS" in upper else None
        if idx is not None:
            pesos_x0 = ws[idx]["x0"]
            if idx + 1 < len(ws) and "LARES" in upper[idx + 1]:
                boundary = (ws[idx]["x1"] + ws[idx + 1]["x0"]) / 2
            else:
                boundary = ws[idx]["x1"] + 15
            if "FECHA" in upper:
                current_section = "detalle"
            elif "CONSOLIDADO" in upper:
                current_section = "consolidado"
            continue

        date = parse_spanish_date(texts[0])

        # Section markers on non-date lines
        if date is None:
            line_text = " ".join(upper)
            for marker in template.section_markers:
                if marker.upper() in line_text:
                    current_section = marker.lower().replace(" ", "_")
                    break
            continue

        # Only parse date rows inside a known table (after a column header)
        if pesos_x0 is None or boundary is None:
            continue

        description_words: list[str] = []
        comprobante = ""
        ars_amount: float | None = None
        usd_amount: float | None = None

        for w in ws[1:]:
            text = w["text"]
            if w["x1"] >= boundary and _AMOUNT_WORD_RE.fullmatch(text):
                value = parse_amount_argentine(text)
                if value and usd_amount is None:
                    usd_amount = value
                continue
            if w["x1"] >= pesos_x0 and _AMOUNT_WORD_RE.fullmatch(text):
                value = parse_amount_argentine(text)
                if value and ars_amount is None:
                    ars_amount = value
                continue
            if not comprobante and w["x1"] < pesos_x0 and _COMPROBANTE_RE.fullmatch(text):
                comprobante = text
                continue
            if w["x1"] < pesos_x0:
                description_words.append(text)

        # Drop trailing bare amounts that belong to a redundant summary column
        # (e.g. "SU PAGO -1.233.608,29" where the value repeats in another column)
        while description_words and _AMOUNT_WORD_RE.fullmatch(description_words[-1]):
            description_words.pop()

        if ars_amount is None and usd_amount is None:
            continue

        base = {
            "date": date,
            "description": " ".join(description_words).strip(),
            "account": template.name,
            "metadata": {"comprobante": comprobante, "seccion": current_section},
        }
        if ars_amount is not None:
            rows.append({**base, "amount": ars_amount, "currency": "ARS"})
        if usd_amount is not None:
            rows.append({**base, "amount": usd_amount, "currency": "USD"})

    return rows


def parse_file(
    file_content: bytes, template_name: str, file_extension: str
) -> list[dict[str, Any]]:
    """Parse file based on template and file type.

    Every returned row carries a normalized ``movement_type``
    (ingreso | gasto | transferencia) and a signed amount where
    positive = money in and negative = money out.
    """
    template = get_template(template_name)
    if not template:
        raise ValueError(f"Template '{template_name}' not found")

    if template.file_type == "excel" or file_extension in [".xlsx", ".xls"]:
        rows = parse_excel(file_content, template)
    elif template.file_type == "csv" or file_extension == ".csv":
        rows = parse_csv(file_content, template)
    elif template.file_type == "pdf" or file_extension == ".pdf":
        rows = parse_pdf(file_content, template)
    else:
        raise ValueError(f"Unsupported file type: {file_extension}")

    template_key = template.name.lower().replace(" ", "_")
    for row in rows:
        hint = row.pop("movement_type_hint", None)
        movement_type, signed_amount = classify_movement(
            template_key, str(row["description"]), float(row["amount"]), hint
        )
        row["movement_type"] = movement_type
        row["amount"] = signed_amount

    return rows
