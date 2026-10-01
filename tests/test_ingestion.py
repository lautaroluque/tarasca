"""Tests for ingestion module."""

import io
from datetime import datetime

import pandas as pd
import pytest

from src.core.ingestion import parse_amount_argentine, parse_excel, parse_file
from src.core.templates import GALICIA_MASTERCARD_TEMPLATE, FIWIND_TEMPLATE


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
