"""Bank template definitions and column mapping."""

from dataclasses import dataclass, field


@dataclass
class BankTemplate:
    """Bank template configuration."""

    name: str
    file_type: str  # 'excel', 'csv', 'pdf'
    description: str
    # For Excel/CSV: mapping of standard fields to column names
    column_mapping: dict[str, str] = field(default_factory=dict)
    # For Excel: sheet name to use
    sheet_name: str | None = None
    # Date format string
    date_format: str | None = None
    # For PDF: section markers
    section_markers: list[str] = field(default_factory=list)
    # For PDF: column positions (if needed)
    column_positions: dict[str, tuple[float, float]] = field(default_factory=dict)
    # Number format: 'argentine' (1.234,56) or 'standard' (1,234.56)
    number_format: str = "standard"
    # Currency columns (for multi-currency PDFs)
    currency_columns: dict[str, str] = field(default_factory=dict)
    # Metadata fields to extract
    metadata_fields: dict[str, str] = field(default_factory=dict)


# Fiwind Excel template
FIWIND_TEMPLATE = BankTemplate(
    name="Fiwind",
    file_type="excel",
    description="Extracto de cuenta Fiwind (Excel)",
    sheet_name="Actividad",
    date_format="%d/%m/%Y %H:%M:%S",
    column_mapping={
        "date": "Fecha",
        "description": "Tipo",
        "amount": "Monto",
        "currency": "Moneda",
    },
    metadata_fields={
        "tipo": "Tipo",
        "monto_origen": "Monto Origen",
        "moneda_origen": "Moneda Origen",
        "precio": "Precio",
    },
)

# Galicia Mastercard PDF template
GALICIA_MASTERCARD_TEMPLATE = BankTemplate(
    name="Galicia Mastercard",
    file_type="pdf",
    description="Resumen de tarjeta de crédito Galicia Mastercard (PDF)",
    date_format="%d-%b-%y",
    number_format="argentine",
    section_markers=["COMPRAS DEL MES", "CUOTA DEL MES"],
    currency_columns={
        "ARS": "PESOS",
        "USD": "DÓLARES",
    },
    metadata_fields={
        "comprobante": "COMPROBANTE",
        "seccion": "SECCION",
    },
)

# Registry of all available templates
TEMPLATES: dict[str, BankTemplate] = {
    "fiwind": FIWIND_TEMPLATE,
    "galicia_mastercard": GALICIA_MASTERCARD_TEMPLATE,
}


def get_template(template_name: str) -> BankTemplate | None:
    """Get a template by name."""
    return TEMPLATES.get(template_name.lower())


def list_templates() -> list[BankTemplate]:
    """List all available templates."""
    return list(TEMPLATES.values())
