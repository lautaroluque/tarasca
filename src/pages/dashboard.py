"""Dashboard page: combined multi-currency balances plus monthly flows.

The headline is one figure across ARS/USD/USDT ("Patrimonio"), built from
every imported movement plus an opening balance per account/currency, and
converted with rates read from the user's own swaps (see ``src/core/fx``).
The monthly section below keeps the per-period view, but its flows are also
expressed in the selected base currency so income and spending in different
currencies are comparable.

Transfers between the user's own accounts never enter the expense metrics:
``movement_type == "gasto"`` is what those metrics count, and a transfer
between own accounts is classified as ``transferencia``.
"""

from datetime import datetime
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

from src.core.database import (
    get_all_transactions,
    get_categories,
    get_setting_json,
    set_setting_json,
)
from src.core.fx import RateTable, build_rate_table, collect_rate_samples

# ARS is the pivot every swap touches; the switcher picks the display unit.
BASE_CURRENCIES = ("ARS", "USD", "USDT")

# Settings key holding {"<account>::<currency>": opening_balance}.
OPENING_BALANCES_KEY = "opening_balances"


def _balance_key(account: str, currency: str) -> str:
    return f"{account}::{currency}"


def _movement_by_account_currency(
    history: list[dict[str, Any]],
) -> dict[tuple[str, str], float]:
    """Net movement per (account, currency) across all imported rows."""
    totals: dict[tuple[str, str], float] = {}
    for row in history:
        key = (row["account"], row["currency"])
        totals[key] = totals.get(key, 0.0) + float(row["amount"])
    return totals


def _rates(history: list[dict[str, Any]]) -> RateTable:
    """Rate table built from the swaps already present in ``history``."""
    return build_rate_table(collect_rate_samples(history))


def _convert(
    amount: float, source: str, target: str, rates: RateTable
) -> float | None:
    """Convert, or None when either side has no rate of its own."""
    if not (rates.has_rate(source) and rates.has_rate(target)):
        return None
    return rates.convert(amount, source, target)


def _rates_caption(rates: RateTable, base_currency: str) -> str:
    """Human-readable provenance for the rates used on this page."""
    if not rates.has_rate(base_currency) or len(rates.ars_per_unit) <= 1:
        return "Todavía no hay conversiones propias registradas para armar tasas."
    parts = []
    for currency in sorted(rates.ars_per_unit):
        if currency == base_currency:
            continue
        value = rates.convert(1.0, currency, base_currency)
        count = rates.sample_counts.get(currency, 0)
        newest = rates.newest_sample.get(currency)
        since = f", swap del {newest.date().isoformat()}" if newest else ""
        parts.append(
            f"1 {currency} = {value:,.2f} {base_currency} "
            f"({count} conversiones{since})"
        )
    return "Tasas de tus propios swaps · " + " · ".join(parts)


def _render_net_worth(
    history: list[dict[str, Any]],
    rates: RateTable,
    base_currency: str,
) -> None:
    """Combined balance across currencies, with an opening-balance editor."""
    movements = _movement_by_account_currency(history)
    opening = get_setting_json(OPENING_BALANCES_KEY, {})

    pairs = set(movements)
    for key in opening:
        account, _, currency = key.partition("::")
        pairs.add((account, currency))
    ordered_pairs = sorted(pairs)

    with st.expander("✏️ Editar saldos iniciales"):
        st.caption(
            "Saldo de cada cuenta antes del primer movimiento importado. "
            "Sin esto, el balance es solo la suma desde el primer registro."
        )
        with st.form("opening_balances_form"):
            columns = st.columns(3)
            values: dict[str, float] = {}
            for index, (account, currency) in enumerate(ordered_pairs):
                key = _balance_key(account, currency)
                session_key = f"opening_{account}_{currency}"
                if session_key not in st.session_state:
                    st.session_state[session_key] = float(opening.get(key, 0.0))
                with columns[index % len(columns)]:
                    values[key] = st.number_input(
                        f"{account} · {currency}",
                        key=session_key,
                        format="%.2f",
                    )
            saved = st.form_submit_button("Guardar")
            if saved:
                set_setting_json(OPENING_BALANCES_KEY, values)
                st.session_state["opening_balances_saved"] = True
                st.rerun()

    if st.session_state.pop("opening_balances_saved", False):
        st.success("Saldos iniciales guardados.")

    rows = []
    total = 0.0
    unpriced: set[str] = set()
    for account, currency in ordered_pairs:
        key = _balance_key(account, currency)
        initial = float(opening.get(key, 0.0))
        movement = movements.get((account, currency), 0.0)
        balance = initial + movement
        equivalent = _convert(balance, currency, base_currency, rates)
        if equivalent is None:
            unpriced.add(currency)
        else:
            total += equivalent
        rows.append(
            {
                "Cuenta": account,
                "Moneda": currency,
                "Saldo inicial": initial,
                "Movimiento": movement,
                "Saldo": balance,
                f"Equivalente ({base_currency})": equivalent,
            }
        )

    st.metric(f"Balance total ({base_currency})", f"{total:,.2f}")
    st.caption(_rates_caption(rates, base_currency))
    if unpriced:
        st.warning(
            "Sin tasa propia para: "
            + ", ".join(sorted(unpriced))
            + ". Esos saldos quedan fuera del total."
        )

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.caption(
        "Saldo = saldo inicial + todos los movimientos importados "
        "(transferencias y conversiones incluidas: mueven dinero, no lo gastan)."
    )


def render_dashboard_page() -> None:
    """Render the dashboard page."""
    st.title("📊 Dashboard")

    history = get_all_transactions()
    rates = _rates(history)

    # Default to the month of the most recent transaction, so importing an
    # older statement shows data right away instead of an empty current month
    if history:
        latest_date = datetime.fromisoformat(history[0]["date"])
        default_month, default_year = latest_date.month, latest_date.year
    else:
        default_month, default_year = datetime.now().month, datetime.now().year

    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        base_currency = st.selectbox("Moneda base", list(BASE_CURRENCIES), index=0)

    with col2:
        selected_month = st.selectbox(
            "Mes",
            range(1, 13),
            index=default_month - 1,
            format_func=lambda x: datetime(2000, x, 1).strftime("%B"),
        )

    with col3:
        selected_year = st.number_input(
            "Año", min_value=2000, max_value=2100, value=default_year
        )

    st.markdown("### 💰 Patrimonio")
    _render_net_worth(history, rates, base_currency)

    # Monthly flows, converted to the base currency
    categories = get_categories()

    start_date = datetime(selected_year, selected_month, 1)
    if selected_month == 12:
        end_date = datetime(selected_year + 1, 1, 1)
    else:
        end_date = datetime(selected_year, selected_month + 1, 1)

    transactions = get_all_transactions(start_date=start_date, end_date=end_date)

    if not transactions:
        st.info("No hay transacciones para el período seleccionado.")
        return

    missing_rates: set[str] = set()

    def to_base(amount: float, currency: str) -> float:
        converted = _convert(amount, currency, base_currency, rates)
        if converted is None:
            missing_rates.add(currency)
            return 0.0
        return converted

    # Convert to DataFrame
    df = pd.DataFrame(
        [
            {
                # Supabase returns ISO strings; normalize to naive datetimes so
                # sorting/nlargest work and dates display cleanly
                "date": pd.to_datetime(t["date"], utc=True).tz_localize(None),
                "description": t["description"],
                "amount": t["amount"],
                "amount_base": to_base(float(t["amount"]), t["currency"]),
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

    if missing_rates:
        st.warning(
            "Sin tasa propia para " + ", ".join(sorted(missing_rates))
            + ": esas filas cuentan 0 en los totales combinados."
        )

    # Summary cards
    st.markdown("### Resumen del mes")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_income = df.loc[df["movement_type"] == "ingreso", "amount_base"].sum()
        st.metric("Ingresos", f"{total_income:,.2f} {base_currency}")

    with col2:
        # Gastos are stored as negative amounts (money out)
        total_expenses = df.loc[df["movement_type"] == "gasto", "amount_base"].sum()
        st.metric("Gastos", f"{abs(total_expenses):,.2f} {base_currency}")

    with col3:
        net = total_income + total_expenses
        st.metric("Balance del mes", f"{net:,.2f} {base_currency}")

    with col4:
        transfers = df[df["movement_type"] == "transferencia"]
        st.metric("Transferencias", len(transfers))
        if not transfers.empty:
            moved = transfers["amount_base"].abs().sum()
            st.caption(f"Movido: {moved:,.2f} {base_currency}")

    per_currency = df.groupby("currency")["amount"].sum()
    st.caption(
        "Por moneda (saldo neto del mes): "
        + " · ".join(f"{value:,.2f} {currency}" for currency, value in per_currency.items())
    )

    # Charts
    st.markdown("### Visualizaciones")

    col1, col2 = st.columns(2)

    with col1:
        # Spending by category pie chart (only real spending, not transfers)
        expenses_by_category = (
            df[df["movement_type"] == "gasto"]
            .groupby("category")["amount_base"]
            .sum()
            .abs()
        )

        if not expenses_by_category.empty:
            fig = px.pie(
                values=expenses_by_category.values,
                names=expenses_by_category.index,
                title=f"Gastos por Categoría ({base_currency})",
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
        daily_balance = flows.groupby("day")["amount_base"].sum().cumsum()

        if not daily_balance.empty:
            fig = px.line(
                x=daily_balance.index,
                y=daily_balance.values,
                title=f"Balance Diario ({base_currency})",
                labels={"x": "Día", "y": "Balance"},
            )
            fig.update_traces(mode="lines+markers")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay datos para mostrar.")

    # Account breakdown
    st.markdown("### Desglose por Cuenta")

    account_summary = df.groupby("account")["amount_base"].sum().reset_index()
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
