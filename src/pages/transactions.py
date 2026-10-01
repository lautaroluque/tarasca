"""Transactions page for viewing and managing transactions."""

from datetime import datetime

import streamlit as st

from src.core.database import (
    delete_transaction,
    get_categories,
    get_session,
    get_transactions,
    update_transaction,
)


def render_transactions_page():
    """Render the transactions page."""
    st.title("📋 Transacciones")

    # Filters
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        # Date range filter
        date_range = st.date_input(
            "Rango de fechas",
            value=(datetime.now().replace(day=1), datetime.now()),
            help="Selecciona el rango de fechas",
        )

    with col2:
        # Category filter
        session = next(get_session())
        categories = get_categories(session)
        category_names = ["Todas"] + [c.name for c in categories]
        selected_category = st.selectbox("Categoría", category_names)

    with col3:
        # Account filter
        accounts = ["Todas", "Fiwind", "Galicia Mastercard"]
        selected_account = st.selectbox("Cuenta", accounts)

    with col4:
        # Currency filter
        currencies = ["Todas", "ARS", "USD"]
        selected_currency = st.selectbox("Moneda", currencies)

    # Get transactions
    try:
        start_date = datetime.combine(date_range[0], datetime.min.time()) if date_range else None
        end_date = datetime.combine(date_range[1], datetime.max.time()) if date_range else None
    except (IndexError, TypeError):
        start_date = None
        end_date = None

    category_id = None
    if selected_category != "Todas":
        category = next((c for c in categories if c.name == selected_category), None)
        if category:
            category_id = category.id

    account = None if selected_account == "Todas" else selected_account
    currency = None if selected_currency == "Todas" else selected_currency

    transactions = get_transactions(
        session,
        category_id=category_id,
        account=account,
        currency=currency,
        start_date=start_date,
        end_date=end_date,
        limit=1000,
    )

    session.close()

    if not transactions:
        st.info("No se encontraron transacciones con los filtros seleccionados.")
        return

    st.caption(f"Mostrando {len(transactions)} transacciones")

    # Display transactions
    for transaction in transactions:
        with st.container():
            col1, col2, col3, col4, col5 = st.columns([2, 3, 2, 2, 1])

            with col1:
                st.write(f"**{transaction.date.strftime('%d/%m/%Y')}**")

            with col2:
                st.write(transaction.description)
                # Show metadata if available
                if transaction.metadata:
                    metadata_str = ", ".join(
                        [f"{k}: {v}" for k, v in transaction.metadata.items()]
                    )
                    st.caption(f"📎 {metadata_str}")

            with col3:
                amount_color = "red" if transaction.amount < 0 else "green"
                st.write(
                    f":{amount_color}[**{transaction.amount:,.2f} {transaction.currency}**]"
                )

            with col4:
                # Category selector
                category_names = [c.name for c in categories]
                current_category = "Otros"
                if transaction.category_id:
                    category = next(
                        (c for c in categories if c.id == transaction.category_id), None
                    )
                    if category:
                        current_category = category.name

                new_category = st.selectbox(
                    "Categoría",
                    category_names,
                    index=category_names.index(current_category)
                    if current_category in category_names
                    else 0,
                    key=f"cat_{transaction.id}",
                )

                if new_category != current_category:
                    # Update category
                    new_category_obj = next(
                        (c for c in categories if c.name == new_category), None
                    )
                    if new_category_obj:
                        session = next(get_session())
                        try:
                            update_transaction(
                                session, transaction.id, {"category_id": new_category_obj.id}
                            )
                            st.success("Categoría actualizada")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
                        finally:
                            session.close()

            with col5:
                if st.button("🗑️", key=f"del_{transaction.id}", help="Eliminar"):
                    session = next(get_session())
                    try:
                        delete_transaction(session, transaction.id)
                        st.success("Transacción eliminada")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
                    finally:
                        session.close()

            st.divider()
