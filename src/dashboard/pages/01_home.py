import streamlit as st
import plotly.express as px

from src.dashboard.db import (
    get_available_years,
    get_home_metrics,
    get_sector_breakdown,
    get_top_companies,
)


def format_number(value, suffix=""):
    """
    Format dashboard KPI values.
    """

    if value is None:
        return "N/A"

    return f"{value:,.2f}{suffix}"


def render():

    # ----------------------------------------------
    # TITLE
    # ----------------------------------------------

    st.title("🏠 Nifty 100 Analytics")

    st.caption(
        "Financial analytics dashboard for Nifty 100 companies"
    )


    # ----------------------------------------------
    # YEAR SELECTOR
    # ----------------------------------------------

    available_years = get_available_years()

    dashboard_years = []

    for year in available_years:

        try:
            year_number = int(str(year)[:4])

            if 2019 <= year_number <= 2024:
                dashboard_years.append(year)

        except (ValueError, TypeError):
            pass

    dashboard_years = sorted(
        dashboard_years,
        reverse=True,
    )

    if not dashboard_years:

        st.warning(
            "No financial years between 2019 and 2024 were found."
        )

        return

    if "dashboard_year" not in st.session_state:

        st.session_state.dashboard_year = (
            dashboard_years[0]
        )

    st.sidebar.divider()

    st.sidebar.subheader("Dashboard Settings")

    selected_year = st.sidebar.selectbox(
        "Financial Year",
        options=dashboard_years,
        key="dashboard_year",
    )


    # ----------------------------------------------
    # LOAD DATA
    # ----------------------------------------------

    metrics = get_home_metrics(selected_year)


    # ----------------------------------------------
    # KPI TILES
    # ----------------------------------------------

    st.subheader(
        f"Dashboard Summary — {selected_year}"
    )

    row_1 = st.columns(3)

    row_1[0].metric(
        "Average ROE",
        format_number(
            metrics["average_roe"],
            "%",
        ),
    )

    row_1[1].metric(
        "Median P/E",
        format_number(
            metrics["median_pe"],
        ),
    )

    row_1[2].metric(
        "Median D/E",
        format_number(
            metrics["median_debt_to_equity"],
        ),
    )


    row_2 = st.columns(3)

    row_2[0].metric(
        "Total Companies",
        metrics["total_companies"],
    )

    row_2[1].metric(
        "Median Revenue CAGR 5yr",
        format_number(
            metrics["median_revenue_cagr_5yr"],
            "%",
        ),
    )

    row_2[2].metric(
        "Debt-Free Companies",
        metrics["debt_free_companies"],
    )


    st.divider()


    # ----------------------------------------------
    # SECTOR DONUT CHART
    # ----------------------------------------------

    left_column, right_column = st.columns(
        [1, 1]
    )

    with left_column:

        st.subheader(
            "Sector Breakdown"
        )

        sector_data = get_sector_breakdown(
            selected_year
        )

        if sector_data.empty:

            st.info(
                "No sector data available."
            )

        else:

            figure = px.pie(
                sector_data,
                names="broad_sector",
                values="company_count",
                hole=0.55,
            )

            figure.update_traces(
                textposition="inside",
                textinfo="percent+label",
            )

            figure.update_layout(
                height=500,
                legend_title_text="Sector",
            )

            st.plotly_chart(
                figure,
                use_container_width=True,
            )


    # ----------------------------------------------
    # TOP 5 TABLE
    # ----------------------------------------------

    with right_column:

        st.subheader(
            "Top 5 Companies by Quality Score"
        )

        top_companies = get_top_companies(
            selected_year
        )

        if top_companies.empty:

            st.info(
                "No quality score data available."
            )

        else:

            display_dataframe = (
                top_companies.copy()
            )

            if (
                "composite_quality_score"
                in display_dataframe.columns
            ):

                display_dataframe[
                    "composite_quality_score"
                ] = display_dataframe[
                    "composite_quality_score"
                ].round(2)

            if (
                "return_on_equity_pct"
                in display_dataframe.columns
            ):

                display_dataframe[
                    "return_on_equity_pct"
                ] = display_dataframe[
                    "return_on_equity_pct"
                ].round(2)

            if (
                "debt_to_equity"
                in display_dataframe.columns
            ):

                display_dataframe[
                    "debt_to_equity"
                ] = display_dataframe[
                    "debt_to_equity"
                ].round(2)

            st.dataframe(
                display_dataframe,
                use_container_width=True,
                hide_index=True,
            )


    # ----------------------------------------------
    # FOOTER
    # ----------------------------------------------

    st.divider()

    st.caption(
        "Nifty 100 Analytics • Data sourced from the project SQLite database"
    )