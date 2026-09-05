import streamlit as st

from src.dashboard.utils.db import get_companies


def render():

    st.title("🏠 Nifty 100 Analytics")

    st.markdown(
        """
        Welcome to the **Nifty 100 Financial Analytics Dashboard**.

        Use the navigation menu on the left to explore:

        - 🏢 Company financial profiles
        - 🔎 Financial screeners
        - 👥 Peer group comparisons
        - 📈 Financial trends
        - 🏭 Sector analysis
        - 💰 Capital and cash-flow analysis
        - 📄 Generated reports
        """
    )

    st.divider()

    companies = get_companies()

    total_companies = len(companies)

    sectors = (
        companies["broad_sector"]
        .dropna()
        .nunique()
    )

    sub_sectors = (
        companies["sub_sector"]
        .dropna()
        .nunique()
    )

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Companies",
        total_companies,
    )

    col2.metric(
        "Broad Sectors",
        sectors,
    )

    col3.metric(
        "Sub Sectors",
        sub_sectors,
    )

    st.divider()

    st.subheader("Companies")

    st.dataframe(
        companies,
        use_container_width=True,
        hide_index=True,
    )