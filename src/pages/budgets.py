"""Budgets page for creating and tracking budgets."""

from datetime import datetime

import pandas as pd
import streamlit as st

from src.core.database import (
    create_budget,
    delete_budget,
    get_budgets,
    get_categories,
    get_session,
    get_transactions,
)


def render_budgets_page():
    """Render the budgets page."""
    st.title("🎯 Presupuestos")

    # Month/Year selector
    col1, col2 = st.columns(2)
    with col1:
        current_month = datetime.now().month
        selected_month = st.selectbox(
            "Mes",
            range(1, 13),
            index=current_month - 1,
            format_func=lambda x: datetime(2000, x, 1).strftime("%B"),
        )

    with col2:
        current_year = datetime.now().year
        selected_year = st.number_input("Año", min_value=2000, max_value=2100, value=current_year)

    # Get budgets for selected month/year
    session = next(get_session())
    budgets = get_budgets(session, month=selected_month, year=selected_year)
    categories = get_categories(session)

    # Get actual spending
    start_date = datetime(selected_year, selected_month, 1)
    if selected_month == 12:
        end_date = datetime(selected_year + 1, 1, 1)
    else:
        end_date = datetime(selected_year, selected_month + 1, 1)

    transactions = get_transactions(
        session,
        start_date=start_date,
        end_date=end_date,
        limit=10000,
    )

    session.close()

    # Calculate actual spending by category
    if transactions:
        df = pd.DataFrame(
            [
                {
                    "category_id": t.category_id,
                    "amount": t.amount,
                    "currency": t.currency,
                }
                for t in transactions
            ]
        )

        # Get category names
        category_map = {c.id: c.name for c in categories}
        df["category"] = df["category_id"].map(category_map).fillna("Otros")

        # Sum expenses by category (only negative amounts)
        expenses_by_category = (
            df[df["amount"] < 0].groupby("category")["amount"].sum().abs()
        )
    else:
        expenses_by_category = pd.Series(dtype=float)

    # Display budgets
    st.markdown("### Presupuestos del Mes")

    if not budgets:
        st.info("No hay presupuestos para este mes. Crea uno abajo.")
    else:
        for budget in budgets:
            category = next((c for c in categories if c.id == budget.category_id), None)
            category_name = category.name if category else "Desconocida"

            # Get actual spending for this category
            actual = expenses_by_category.get(category_name, 0.0)

            # Calculate progress
            if budget.amount > 0:
                progress = min(actual / budget.amount, 1.0)
            else:
                progress = 0.0

            # Display budget card
            with st.container():
                col1, col2, col3 = st.columns([3, 2, 1])

                with col1:
                    st.write(f"**{category_name}**")
                    st.caption(f"Presupuesto: {budget.amount:,.2f} {budget.currency}")

                with col2:
                    st.write(f"**Gastado: {actual:,.2f}**")
                    st.progress(progress)

                with col3:
                    if st.button("🗑️", key=f"del_budget_{budget.id}", help="Eliminar"):
                        session = next(get_session())
                        try:
                            delete_budget(session, budget.id)
                            st.success("Presupuesto eliminado")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
                        finally:
                            session.close()

                st.divider()

    # Create new budget
    st.markdown("### Crear Nuevo Presupuesto")

    col1, col2, col3 = st.columns(3)

    with col1:
        category_names = [c.name for c in categories]
        new_category = st.selectbox("Categoría", category_names)

    with col2:
        new_amount = st.number_input(
            "Monto",
            min_value=0.0,
            value=10000.0,
            step=1000.0,
            format="%.2f",
        )

    with col3:
        new_currency = st.selectbox("Moneda", ["ARS", "USD"], key="budget_currency")

    if st.button("➕ Crear Presupuesto", type="primary"):
        category = next((c for c in categories if c.name == new_category), None)
        if category:
            session = next(get_session())
            try:
                create_budget(
                    session,
                    {
                        "category_id": category.id,
                        "amount": new_amount,
                        "currency": new_currency,
                        "month": selected_month,
                        "year": selected_year,
                    },
                )
                st.success("Presupuesto creado exitosamente")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {str(e)}")
            finally:
                session.close()
