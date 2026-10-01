"""Upload page for importing bank extracts."""

import streamlit as st

from src.core.categorization import categorize_transaction, get_default_categories
from src.core.database import create_transactions_bulk, get_categories
from src.core.ingestion import parse_file
from src.core.templates import list_templates


def render_upload_page() -> None:
    """Render the upload page."""
    st.title("📤 Importar Extractos")

    st.markdown("Sube tus extractos bancarios para importar transacciones automáticamente.")

    # File upload
    uploaded_file = st.file_uploader(
        "Selecciona un archivo",
        type=["xlsx", "xls", "csv", "pdf"],
        help="Formatos soportados: Excel (.xlsx, .xls), CSV, PDF",
    )

    if uploaded_file is not None:
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
            st.info(f"Archivo: **{uploaded_file.name}**")

        # Parse button
        if st.button("🔍 Previsualizar", type="primary"):
            try:
                # Parse file
                file_content = uploaded_file.getvalue()
                file_extension = uploaded_file.name.split(".")[-1]

                with st.spinner("Procesando archivo..."):
                    transactions = parse_file(
                        file_content,
                        selected_template.lower().replace(" ", "_"),
                        file_extension,
                    )

                if not transactions:
                    st.warning("No se encontraron transacciones en el archivo.")
                    return

                # Categorize transactions
                categories = get_default_categories()
                for transaction in transactions:
                    category_name = categorize_transaction(
                        transaction["description"], categories
                    )
                    transaction["category_name"] = category_name or "Otros"

                # Show preview
                st.success(f"Se encontraron **{len(transactions)}** transacciones")

                # Display preview table
                st.markdown("### Previsualización")

                preview_data = []
                for t in transactions[:10]:  # Show first 10
                    preview_data.append(
                        {
                            "Fecha": t["date"].strftime("%d/%m/%Y"),
                            "Descripción": t["description"],
                            "Monto": f"{t['amount']:,.2f}",
                            "Moneda": t["currency"],
                            "Categoría": t["category_name"],
                            "Metadatos": str(t.get("metadata", {})),
                        }
                    )

                st.dataframe(preview_data, use_container_width=True)

                if len(transactions) > 10:
                    st.caption(f"Mostrando 10 de {len(transactions)} transacciones")

                # Import button
                if st.button("💾 Importar a la base de datos", type="primary"):
                    with st.spinner("Importando transacciones..."):
                        # Get categories from database to map names to IDs
                        db_categories = get_categories()
                        category_name_to_id = {c["name"]: c["id"] for c in db_categories}

                        # Prepare data for database
                        db_transactions = []
                        for t in transactions:
                            category_name = t.get("category_name", "Otros")
                            category_id = category_name_to_id.get(category_name)

                            db_transactions.append(
                                {
                                    "date": t["date"].isoformat(),
                                    "description": t["description"],
                                    "amount": t["amount"],
                                    "currency": t["currency"],
                                    "account": t["account"],
                                    "category_id": category_id,
                                    "metadata": t.get("metadata", {}),
                                }
                            )

                        count = create_transactions_bulk(db_transactions)
                        st.success(
                            f"✅ Se importaron **{count}** transacciones exitosamente"
                        )

            except Exception as e:
                st.error(f"Error al procesar el archivo: {str(e)}")
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
""")
