"""Upload page for importing bank extracts."""

from datetime import datetime, timedelta, timezone

import streamlit as st

from src.core.categorization import categorize_transaction, get_default_categories
from src.core.database import (
    create_transactions_bulk,
    get_all_transactions,
    get_categories,
    get_supabase_client,
)
from src.core.ingestion import parse_file
from src.core.merging import merge_with_existing
from src.core.templates import list_templates


def _set_flash(type_: str, message: str) -> None:
    """Store a one-shot message that survives the st.rerun() after import."""
    st.session_state["import_flash"] = {"type": type_, "message": message}


def _dedupe_key(row: dict) -> tuple:
    """Key that identifies a transaction already present in the database.

    Accepts both parsed rows (naive datetime) and rows returned by Supabase
    (ISO string, possibly timezone-aware) and normalizes them to UTC-naive.
    """
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


def _list_phone_files() -> list[dict]:
    """List files shared from the phone, newest first."""
    client = get_supabase_client()
    objects = client.storage.from_("imports").list()
    return sorted(objects, key=lambda o: o.get("created_at") or "", reverse=True)


def _download_phone_file(path: str) -> bytes:
    """Download a file shared from the phone."""
    client = get_supabase_client()
    return client.storage.from_("imports").download(path)


def _parse_and_store(file_content: bytes, template_name: str, file_extension: str) -> None:
    """Parse the file, categorize transactions and store them in session state."""
    with st.spinner("Procesando archivo..."):
        transactions = parse_file(file_content, template_name, file_extension)

    if not transactions:
        st.warning("No se encontraron transacciones en el archivo.")
        st.session_state.pop("parsed_transactions", None)
        return

    # Categorize transactions
    categories = get_default_categories()
    for transaction in transactions:
        category_name = categorize_transaction(transaction["description"], categories)
        transaction["category_name"] = category_name or "Otros"

    st.session_state["parsed_transactions"] = transactions
    st.session_state["parsed_count"] = len(transactions)


def _render_preview(transactions: list[dict]) -> None:
    """Render the parsed transactions preview table."""
    st.success(f"Se encontraron **{len(transactions)}** transacciones")
    st.markdown("### Previsualización")

    preview_data = []
    for t in transactions[:10]:  # Show first 10
        preview_data.append(
            {
                "Fecha": t["date"].strftime("%d/%m/%Y"),
                "Descripción": t["description"],
                "Monto": f"{t['amount']:,.2f}",
                "Moneda": t["currency"],
                "Tipo": t.get("movement_type", "gasto"),
                "Categoría": t["category_name"],
                "Metadatos": str(t.get("metadata", {})),
            }
        )

    st.dataframe(preview_data, use_container_width=True)

    if len(transactions) > 10:
        st.caption(f"Mostrando 10 de {len(transactions)} transacciones")


def _import_transactions(transactions: list[dict]) -> None:
    """Insert the parsed transactions into the database."""
    with st.spinner("Importando transacciones..."):
        # Get categories from database to map names to IDs
        db_categories = get_categories()
        category_name_to_id = {c["name"]: c["id"] for c in db_categories}

        # Prepare data for database
        db_transactions = []
        for t in transactions:
            category_id = category_name_to_id.get(t.get("category_name", "Otros"))

            db_transactions.append(
                {
                    "date": t["date"].isoformat(),
                    "description": t["description"],
                    "amount": t["amount"],
                    "currency": t["currency"],
                    "movement_type": t.get("movement_type", "gasto"),
                    "account": t["account"],
                    "category_id": category_id,
                    "metadata": t.get("metadata", {}),
                    "source": t.get("source", "extracto"),
                }
            )

        # Skip transactions already in the database (re-importing the same file).
        # get_all_transactions pages past Supabase's 1000-row cap so dedupe
        # cannot miss existing rows and import duplicates.
        dates = [t["date"] for t in transactions]
        existing = get_all_transactions(
            start_date=min(dates),
            end_date=max(dates),
        )
        existing_keys = {_dedupe_key(t) for t in existing}
        new_transactions = [t for t in db_transactions if _dedupe_key(t) not in existing_keys]
        skipped = len(db_transactions) - len(new_transactions)

        # Cross-source merge: skip rows already tracked via email notifications
        if new_transactions:
            merge_existing = get_all_transactions(
                start_date=min(dates) - timedelta(days=3),
                end_date=max(dates) + timedelta(days=3),
            )
            new_transactions, merge_skipped = merge_with_existing(
                new_transactions, merge_existing
            )
            skipped += merge_skipped

        if not new_transactions:
            _set_flash(
                "info",
                f"Las **{len(db_transactions)}** transacciones ya están "
                "importadas; no hay nada nuevo que agregar.",
            )
        else:
            count = create_transactions_bulk(new_transactions)
            message = f"✅ Se importaron **{count}** transacciones exitosamente"
            if skipped:
                message += f" ({skipped} ya existían y se omitieron)"
            _set_flash("success", message)

        # Clear preview state so it can't be imported twice
        st.session_state.pop("parsed_transactions", None)
        st.session_state.pop("parsed_count", None)
        st.session_state.pop("phone_file_content", None)
        st.session_state.pop("phone_file_name", None)


def render_upload_page() -> None:
    """Render the upload page."""
    st.title("📤 Importar Extractos")

    # Message from the previous run's import (st.rerun wipes in-run messages)
    flash = st.session_state.pop("import_flash", None)
    if flash:
        getattr(st, flash["type"])(flash["message"])

    st.markdown("Sube tus extractos bancarios para importar transacciones automáticamente.")

    # Source selection: browser upload or phone upload
    source = st.radio(
        "Origen del archivo",
        ["Subir archivo", "Desde el teléfono"],
        horizontal=True,
        help="Desde el teléfono: archivos compartidos con la app de Tarasca",
    )

    if source == "Subir archivo":
        st.session_state.pop("phone_file_content", None)
        st.session_state.pop("phone_file_name", None)
        uploaded_file = st.file_uploader(
            "Selecciona un archivo",
            type=["xlsx", "xls", "csv", "pdf"],
            help="Formatos soportados: Excel (.xlsx, .xls), CSV, PDF",
        )
        file_content = uploaded_file.getvalue() if uploaded_file is not None else None
        file_name = uploaded_file.name if uploaded_file is not None else None
    else:
        phone_files = _list_phone_files()
        if not phone_files:
            st.info(
                "No hay archivos del teléfono. Compartí un extracto con la app "
                "de Tarasca y aparecerá acá."
            )
        else:
            selected_name = st.selectbox(
                "Archivo del teléfono",
                [f["name"] for f in phone_files],
                help="Archivos compartidos con la app de Tarasca",
            )
            if st.button("📥 Usar este archivo", type="primary"):
                try:
                    st.session_state["phone_file_content"] = _download_phone_file(selected_name)
                    st.session_state["phone_file_name"] = selected_name
                except Exception as e:
                    st.error(f"Error al descargar el archivo: {str(e)}")
                    st.exception(e)
        file_content = st.session_state.get("phone_file_content")
        file_name = st.session_state.get("phone_file_name")

    if file_content is not None and file_name is not None:
        # Template selection
        templates = list_templates()
        template_names = [t.name for t in templates]

        col1, col2 = st.columns([2, 1])
        with col1:
            selected_template = st.selectbox(
                "Selecciona el banco/entidad",
                template_names,
                help="Selecciona el banco o entidad del extracto",
            )

        with col2:
            st.info(f"Archivo: **{file_name}**")

        template_key = selected_template.lower().replace(" ", "_")
        # Invalidate any preview when the source file or template changes
        preview_source = f"{file_name}:{template_key}"
        if st.session_state.get("preview_source") != preview_source:
            st.session_state.pop("parsed_transactions", None)
            st.session_state.pop("parsed_count", None)
            st.session_state["preview_source"] = preview_source

        # Parse button
        if st.button("🔍 Previsualizar", type="primary"):
            try:
                _parse_and_store(
                    file_content,
                    template_key,
                    file_name.split(".")[-1],
                )
            except Exception as e:
                st.session_state.pop("parsed_transactions", None)
                st.error(f"Error al procesar el archivo: {str(e)}")
                st.exception(e)

        # Preview and import render from session state, so they survive reruns
        transactions = st.session_state.get("parsed_transactions")
        if transactions:
            try:
                _render_preview(transactions)
            except Exception as e:
                st.error(f"Error al mostrar la previsualización: {str(e)}")

            if st.button("💾 Importar a la base de datos", type="primary"):
                try:
                    _import_transactions(transactions)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al importar: {str(e)}")
                    st.exception(e)

    # Help section
    with st.expander("ℹ️ Formatos soportados"):
        st.markdown("""
### Fiwind (Excel)
- Archivo: `.xlsx`
- Hoja: "Actividad"
- Columnas: Fecha, Tipo, Monto, Moneda, Monto Origen, Moneda Origen, Precio

### Galicia Mastercard (PDF)
- Archivo: `.pdf`
- Sección: "DETALLE DEL CONSUMO"
- Columnas: Fecha, Referencia, Comprobante, Pesos, Dólares
- Formato de números: argentino (1.234,56)

### Tipos de movimiento
Cada transacción se clasifica automáticamente como **Ingreso**, **Gasto** o
**Transferencia** (pagos de tarjeta, conversiones entre saldos, retiros).
Los montos se guardan con signo: positivo = entra dinero, negativo = sale dinero.
Podés corregir el tipo desde la página de Transacciones.
""")
