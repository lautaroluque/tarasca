"""Tarasca - Personal Financial Tracker."""

import streamlit as st

st.set_page_config(
    page_title="Tarasca",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Navigation
st.sidebar.title("💰 Tarasca")
st.sidebar.caption("Tu rastreador financiero personal")

page = st.sidebar.radio(
    "Navegación",
    ["Dashboard", "Importar", "Transacciones", "Presupuestos"],
    index=0,
)

st.sidebar.markdown("---")
st.sidebar.markdown("### Acerca de")
st.sidebar.caption(
    "Tarasca es una aplicación de seguimiento financiero personal. "
    "Importa extractos bancarios, categoriza transacciones y visualiza tus finanzas."
)

# Render selected page
if page == "Dashboard":
    from src.pages.dashboard import render_dashboard_page

    render_dashboard_page()
elif page == "Importar":
    from src.pages.upload import render_upload_page

    render_upload_page()
elif page == "Transacciones":
    from src.pages.transactions import render_transactions_page

    render_transactions_page()
elif page == "Presupuestos":
    from src.pages.budgets import render_budgets_page

    render_budgets_page()
