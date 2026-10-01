"""Transactions page for viewing and managing transactions."""

from datetime import datetime

import streamlit as st

from src.core.database import (
    delete_transaction,
    get_categories,
    get_transactions,
    update_transaction,
)


def render_transactions_page() -> None:
    """Render the transactions page."""
    st.title("📋 Transacciones")

    # Filters
    col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])

    with col1:
        # Date range filter
        date_range = st.date_input(
            "Rango de fechas",
            value=(datetime.now().replace(day=1), datetime.now()),
            help="Selecciona el rango de fechas",
        )

    with col2:
        # Category filter
        categories = get_categories()
        category_names = ["Todas"] + [c["name"] for c in categories]
        selected_category = st.selectbox("Categoría", category_names)

    with col3:
        # Account filter
        accounts = ["Todas", "Fiwind", "Galicia Mastercard"]
        selected_account = st.selectbox("Cuenta", accounts)

    with col4:
        # Currency filter
        currencies = ["Todas", "ARS", "USD", "USDT"]
        selected_currency = st.selectbox("Moneda", currencies)

    with col5:
        # Movement type filter
        movement_labels = {
            "Todos": None,
            "Gasto": "gasto",
            "Ingreso": "ingreso",
            "Transferencia": "transferencia",
        }
        selected_movement = st.selectbox("Tipo", list(movement_labels))

    # Get transactions
    try:
        if date_range and len(date_range) == 2:
            start_date = datetime.combine(date_range[0], datetime.min.time())
            end_date = datetime.combine(date_range[1], datetime.max.time())
        else:
            start_date = None
            end_date = None
    except (IndexError, TypeError):
        start_date = None
        end_date = None

    category_id = None
    if selected_category != "Todas":
        category = next((c for c in categories if c["name"] == selected_category), None)
        if category:
            category_id = category["id"]

    account = None if selected_account == "Todas" else selected_account
    currency = None if selected_currency == "Todas" else selected_currency
    movement_type = movement_labels[selected_movement]

    transactions = get_transactions(
        category_id=category_id,
        account=account,
        currency=currency,
        movement_type=movement_type,
        start_date=start_date,
        end_date=end_date,
        limit=1000,
    )

    if not transactions:
        st.info("No se encontraron transacciones con los filtros seleccionados.")
        return

    st.caption(f"Mostrando {len(transactions)} transacciones")

    movement_types = {
        "gasto": "Gasto",
        "ingreso": "Ingreso",
        "transferencia": "Transferencia",
    }

    # Display transactions
    for transaction in transactions:
        with st.container():
            col1, col2, col3, col4, col5, col6 = st.columns([2, 3, 1.5, 1.5, 2, 1])

            with col1:
                st.write(f"**{transaction['date'][:10]}**")

            with col2:
                st.write(transaction["description"])
                # Show metadata if available
                metadata = transaction.get("metadata", {})
                if metadata:
                    metadata_str = ", ".join(
                        [f"{k}: {v}" for k, v in metadata.items()]
                    )
                    st.caption(f"📎 {metadata_str}")

            with col3:
                amount = transaction["amount"]
                amount_color = "red" if amount < 0 else "green"
                st.write(f":{amount_color}[**{amount:,.2f} {transaction['currency']}**]")

            with col4:
                # Movement type selector (ingreso / gasto / transferencia)
                current_type = transaction.get("movement_type", "gasto")
                type_labels = list(movement_types.values())
                new_type = st.selectbox(
                    "Tipo",
                    type_labels,
                    index=type_labels.index(movement_types[current_type])
                    if current_type in movement_types
                    else 0,
                    key=f"type_{transaction['id']}",
                )

                if movement_types[current_type] != new_type:
                    new_type_value = next(
                        k for k, v in movement_types.items() if v == new_type
                    )
                    try:
                        update_transaction(
                            transaction["id"], {"movement_type": new_type_value}
                        )
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {str(e)}")

            with col5:
                # Category selector
                category_names = [c["name"] for c in categories]
                current_category = "Otros"
                if transaction.get("category_id"):
                    category = next(
                        (c for c in categories if c["id"] == transaction["category_id"]),
                        None,
                    )
                    if category:
                        current_category = category["name"]

                new_category = st.selectbox(
                    "Categoría",
                    category_names,
                    index=(
                        category_names.index(current_category)
                        if current_category in category_names
                        else 0
                    ),
                    key=f"cat_{transaction['id']}",
                )

                if new_category != current_category:
                    # Update category
                    new_category_obj = next(
                        (c for c in categories if c["name"] == new_category), None
                    )
                    if new_category_obj:
                        try:
                            update_transaction(
                                transaction["id"], {"category_id": new_category_obj["id"]}
                            )
                            st.success("Categoría actualizada")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {str(e)}")

            with col6:
                if st.button("🗑️", key=f"del_{transaction['id']}", help="Eliminar"):
                    try:
                        delete_transaction(transaction["id"])
                        st.success("Transacción eliminada")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {str(e)}")

            st.divider()
