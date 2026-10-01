"""File parsing and ingestion logic."""

import io
import re
from datetime import datetime
from typing import Any

import pandas as pd
import pdfplumber

from src.core.templates import BankTemplate, get_template


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


def parse_excel(file_content: bytes, template: BankTemplate) -> list[dict[str, Any]]:
    """Parse Excel file using template."""
    df = pd.read_excel(io.BytesIO(file_content), sheet_name=template.sheet_name)

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

    return transactions


def parse_csv(file_content: bytes, template: BankTemplate) -> list[dict[str, Any]]:
    """Parse CSV file using template."""
    df = pd.read_csv(io.BytesIO(file_content))

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

    return transactions


def parse_pdf(file_content: bytes, template: BankTemplate) -> list[dict[str, Any]]:
    """Parse PDF file using template (Galicia Mastercard)."""
    transactions = []

    with pdfplumber.open(io.BytesIO(file_content)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue

            lines = text.split("\n")
            current_section = ""

            for line in lines:
                # Detect section markers
                for marker in template.section_markers:
                    if marker in line:
                        current_section = marker.lower().replace(" ", "_")
                        continue

                # Parse transaction lines
                # Format: DD-Mon-YY DESCRIPTION COMPROBANTE AMOUNT
                # Example: 05-Sep-26 NETFLIX.COM (USA,ARS, 30797,00) 00192 20,43
                parsed = _parse_pdf_line(line, template, current_section)
                if parsed:
                    if isinstance(parsed, list):
                        transactions.extend(parsed)
                    else:
                        transactions.append(parsed)

    return transactions


def _parse_pdf_line(
    line: str, template: BankTemplate, section: str
) -> dict[str, Any] | None:
    """Parse a single line from PDF."""
    # Match date pattern: DD-Mon-YY
    date_pattern = r"(\d{2}-[A-Za-z]{3}-\d{2})"
    date_match = re.match(date_pattern, line)

    if not date_match:
        return None

    date_str = date_match.group(1)
    try:
        date = datetime.strptime(date_str, template.date_format or "%d-%b-%y")
    except ValueError:
        return None

    # Remove date from line
    remaining = line[len(date_str) :].strip()

    # Extract amounts (Argentine format: 1.234,56 or 1.234,56-)
    # Pattern: optional minus, digits with dots, comma, 2 decimals
    amount_pattern = r"(-?\d{1,3}(?:\.\d{3})*,\d{2})"
    amounts = re.findall(amount_pattern, remaining)

    if not amounts:
        return None

    # Remove amounts from line to get description and comprobante
    remaining_clean = remaining
    for amount in amounts:
        remaining_clean = remaining_clean.replace(amount, " ").strip()

    # Extract comprobante (5-digit number)
    comprobante_pattern = r"(\d{5})"
    comprobante_match = re.search(comprobante_pattern, remaining_clean)
    comprobante = comprobante_match.group(1) if comprobante_match else ""

    # Remove comprobante from description
    if comprobante:
        remaining_clean = remaining_clean.replace(comprobante, " ").strip()

    # Clean up description
    description = " ".join(remaining_clean.split())

    # Parse amounts
    ars_amount = 0.0
    usd_amount = 0.0

    if len(amounts) >= 1:
        ars_amount = parse_amount_argentine(amounts[0])
    if len(amounts) >= 2:
        usd_amount = parse_amount_argentine(amounts[1])

    # Create transactions for each currency
    result = []
    if ars_amount != 0:
        result.append(
            {
                "date": date,
                "description": description,
                "amount": ars_amount,
                "currency": "ARS",
                "account": template.name,
                "metadata": {
                    "comprobante": comprobante,
                    "seccion": section,
                },
            }
        )

    if usd_amount != 0:
        result.append(
            {
                "date": date,
                "description": description,
                "amount": usd_amount,
                "currency": "USD",
                "account": template.name,
                "metadata": {
                    "comprobante": comprobante,
                    "seccion": section,
                },
            }
        )

    return result if result else None  # type: ignore[return-value]


def parse_file(
    file_content: bytes, template_name: str, file_extension: str
) -> list[dict[str, Any]]:
    """Parse file based on template and file type."""
    template = get_template(template_name)
    if not template:
        raise ValueError(f"Template '{template_name}' not found")

    if template.file_type == "excel" or file_extension in [".xlsx", ".xls"]:
        return parse_excel(file_content, template)
    elif template.file_type == "csv" or file_extension == ".csv":
        return parse_csv(file_content, template)
    elif template.file_type == "pdf" or file_extension == ".pdf":
        return parse_pdf(file_content, template)
    else:
        raise ValueError(f"Unsupported file type: {file_extension}")
