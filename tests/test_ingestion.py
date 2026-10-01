"""Tests for ingestion module."""

import io
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from src.core.ingestion import parse_amount_argentine, parse_excel, parse_file
from src.core.templates import FIWIND_TEMPLATE, GALICIA_MASTERCARD_TEMPLATE

SAMPLES_DIR = Path(__file__).parent.parent / "samples"
GALICIA_SAMPLE = SAMPLES_DIR / "galicia-mastercard" / "Resumen .pdf"
FIWIND_SAMPLE = (
    SAMPLES_DIR / "fiwind" / "Actividad_Fiwind_01-10-2026_31-10-2026.xlsx"
)


def test_parse_amount_argentine():
    """Test Argentine number format parsing."""
    assert parse_amount_argentine("1.234,56") == 1234.56
    assert parse_amount_argentine("0,00") == 0.0
    assert parse_amount_argentine("1.000.000,00") == 1000000.0
    assert parse_amount_argentine("-1.234,56") == -1234.56
    assert parse_amount_argentine("") == 0.0
    assert parse_amount_argentine("invalid") == 0.0


def test_parse_excel_fiwind():
    """Test parsing Fiwind Excel file."""
    # Create a sample Excel file
    data = {
        "Fecha": ["01/10/2026 12:23:53", "01/10/2026 12:21:43"],
        "Tipo": ["Rendimiento bonificado", "Ganancia diaria"],
        "Monto": [26.46, 221.41],
        "Moneda": ["ARS", "ARS"],
        "Monto Origen": [None, None],
        "Moneda Origen": [None, None],
        "Precio": [None, None],
    }
    df = pd.DataFrame(data)

    # Write to bytes
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Actividad", index=False)
    output.seek(0)

    # Parse
    transactions = parse_excel(output.getvalue(), FIWIND_TEMPLATE)

    assert len(transactions) == 2
    assert transactions[0]["description"] == "Rendimiento bonificado"
    assert transactions[0]["amount"] == 26.46
    assert transactions[0]["currency"] == "ARS"
    assert transactions[0]["metadata"]["tipo"] == "Rendimiento bonificado"


def test_parse_pdf_galicia():
    """Test parsing Galicia Mastercard PDF file."""
    # This is a simplified test - in practice, you'd use a real PDF file
    # For now, just verify the template is configured correctly
    assert GALICIA_MASTERCARD_TEMPLATE.name == "Galicia Mastercard"
    assert GALICIA_MASTERCARD_TEMPLATE.file_type == "pdf"
    assert GALICIA_MASTERCARD_TEMPLATE.number_format == "argentine"
    assert "COMPRAS DEL MES" in GALICIA_MASTERCARD_TEMPLATE.section_markers
    assert "CUOTA DEL MES" in GALICIA_MASTERCARD_TEMPLATE.section_markers


def test_parse_file_unsupported_type():
    """Test that unsupported file types raise an error."""
    with pytest.raises(ValueError, match="Template.*not found"):
        parse_file(b"content", "nonexistent_template", ".xlsx")


@pytest.mark.skipif(not GALICIA_SAMPLE.exists(), reason="sample file missing")
def test_parse_pdf_galicia_sample():
    """Parse the real sample statement: no duplicated rows, all months."""
    transactions = parse_file(GALICIA_SAMPLE.read_bytes(), "galicia_mastercard", ".pdf")

    # The statement covers Ago-Sep; Spanish month "Ago" must not be dropped
    assert len(transactions) >= 60
    assert any(t["date"] == datetime(2026, 8, 19) for t in transactions)

    # No row is duplicated (same date, description, currency and comprobante)
    keys = [
        (
            t["date"],
            t["description"],
            t["currency"],
            t["metadata"].get("comprobante"),
        )
        for t in transactions
    ]
    assert len(keys) == len(set(keys))

    # Amounts inside descriptions must not create phantom rows:
    # NETFLIX has an embedded amount but only one statement value (USD)
    netflix = [t for t in transactions if "NETFLIX" in t["description"]]
    assert len(netflix) == 1
    assert netflix[0]["currency"] == "USD"
    assert netflix[0]["amount"] == -20.43

    # Card payments and refunds are classified as their own movement types
    pagos = [t for t in transactions if t["description"].startswith("SU PAGO")]
    assert pagos and all(p["movement_type"] == "transferencia" for p in pagos)
    assert all(p["amount"] > 0 for p in pagos)

    # Purchases are expenses (negative = money out)
    gastos = [t for t in transactions if t["movement_type"] == "gasto"]
    assert gastos and all(g["amount"] < 0 for g in gastos)


@pytest.mark.skipif(not FIWIND_SAMPLE.exists(), reason="sample file missing")
def test_parse_excel_fiwind_sample():
    """Parse the real Fiwind extract: multi-currency and conversions."""
    transactions = parse_file(FIWIND_SAMPLE.read_bytes(), "fiwind", ".xlsx")

    currencies = {t["currency"] for t in transactions}
    assert "ARS" in currencies
    assert "USDT" in currencies

    # A conversion emits both sides of the movement
    conversion = [t for t in transactions if "onversi" in t["description"]]
    assert len(conversion) == 2
    assert {t["currency"] for t in conversion} == {"ARS", "USDT"}
    assert all(t["movement_type"] == "transferencia" for t in conversion)
    assert sum(t["amount"] for t in conversion if t["currency"] == "ARS") == 350000.0
    assert sum(t["amount"] for t in conversion if t["currency"] == "USDT") == -217.53

    # Daily yield is income
    income = [t for t in transactions if t["movement_type"] == "ingreso"]
    assert income and all(t["amount"] > 0 for t in income)
