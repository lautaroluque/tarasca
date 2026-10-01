"""Dashboard page for spending overview and visualizations."""

from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from src.core.database import get_categories, get_transactions


def render_dashboard_page() -> None:
    """Render the dashboard page."""
    st.title("📊 Dashboard")

    # Currency switcher
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        selected_currency = st.selectbox("Moneda", ["ARS", "USD", "USDT"], index=0)

    with col2:
        # Month selector
        current_month = datetime.now().month
        selected_month = st.selectbox(
            "Mes",
            range(1, 13),
            index=current_month - 1,
            format_func=lambda x: datetime(2000, x, 1).strftime("%B"),
        )

    with col3:
        current_year = datetime.now().year
        selected_year = st.number_input(
            "Año", min_value=2000, max_value=2100, value=current_year
        )

    # Get transactions for selected month/year
    categories = get_categories()

    start_date = datetime(selected_year, selected_month, 1)
    if selected_month == 12:
        end_date = datetime(selected_year + 1, 1, 1)
    else:
        end_date = datetime(selected_year, selected_month + 1, 1)

    transactions = get_transactions(
        currency=selected_currency,
        start_date=start_date,
        end_date=end_date,
        limit=10000,
    )

    if not transactions:
        st.info("No hay transacciones para el período seleccionado.")
        return

    # Convert to DataFrame
    df = pd.DataFrame(
        [
            {
                "date": t["date"],
                "description": t["description"],
                "amount": t["amount"],
                "currency": t["currency"],
                "movement_type": t.get("movement_type", "gasto"),
                "category": next(
                    (c["name"] for c in categories if c["id"] == t.get("category_id")),
                    "Otros",
                ),
                "account": t["account"],
            }
            for t in transactions
        ]
    )

    # Summary cards
    st.markdown("### Resumen")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_income = df.loc[df["movement_type"] == "ingreso", "amount"].sum()
        st.metric(f"Ingresos ({selected_currency})", f"{total_income:,.2f}")

    with col2:
        # Gastos are stored as negative amounts (money out)
        total_expenses = df.loc[df["movement_type"] == "gasto", "amount"].sum()
        st.metric(f"Gastos ({selected_currency})", f"{abs(total_expenses):,.2f}")

    with col3:
        net = total_income + total_expenses
        st.metric(f"Balance ({selected_currency})", f"{net:,.2f}")

    with col4:
        transfers = df[df["movement_type"] == "transferencia"]
        st.metric("Transferencias", len(transfers))
        if not transfers.empty:
            moved = transfers["amount"].abs().sum()
            st.caption(f"Movido: {moved:,.2f} {selected_currency}")

    # Charts
    st.markdown("### Visualizaciones")

    col1, col2 = st.columns(2)

    with col1:
        # Spending by category pie chart (only real spending, not transfers)
        expenses_by_category = (
            df[df["movement_type"] == "gasto"].groupby("category")["amount"].sum().abs()
        )

        if not expenses_by_category.empty:
            fig = px.pie(
                values=expenses_by_category.values,
                names=expenses_by_category.index,
                title=f"Gastos por Categoría ({selected_currency})",
                color_discrete_sequence=px.colors.qualitative.Set3,
            )
            fig.update_traces(textposition="inside", textinfo="percent+label")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay gastos para mostrar.")

    with col2:
        # Monthly trend line chart (ingresos + gastos; transfers excluded)
        df["day"] = pd.to_datetime(df["date"]).dt.day
        flows = df[df["movement_type"].isin(["ingreso", "gasto"])]
        daily_balance = flows.groupby("day")["amount"].sum().cumsum()

        if not daily_balance.empty:
            fig = px.line(
                x=daily_balance.index,
                y=daily_balance.values,
                title=f"Balance Diario ({selected_currency})",
                labels={"x": "Día", "y": "Balance"},
            )
            fig.update_traces(mode="lines+markers")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay datos para mostrar.")

    # Account breakdown
    st.markdown("### Desglose por Cuenta")

    account_summary = df.groupby("account")["amount"].sum().reset_index()
    account_summary.columns = ["Cuenta", "Balance"]

    st.dataframe(account_summary, use_container_width=True, hide_index=True)

    # Recent transactions
    st.markdown("### Últimas Transacciones")

    recent = df.nlargest(10, "date")[
        [
            "date",
            "description",
            "amount",
            "currency",
            "movement_type",
            "category",
            "account",
        ]
    ]

    st.dataframe(recent, use_container_width=True, hide_index=True)
