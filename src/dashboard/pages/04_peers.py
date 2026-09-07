from pathlib import Path
import sqlite3

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.analytics.peer import load_peer_groups
from src.analytics.radar import (
    AXES,
    build_radar_dataset,
    get_latest_annual_year,
    get_peer_group_average,
    load_composite_scores,
    load_peer_percentile_data,
)


# --------------------------------------------------
# Paths
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[3]

DATABASE_PATH = (
    PROJECT_ROOT
    / "data"
    / "nifty100.db"
)


# --------------------------------------------------
# Data loading
# --------------------------------------------------

@st.cache_data
def load_peer_dashboard_data():
    """
    Load peer groups, peer percentile rankings,
    composite scores and build the radar dataset.
    """

    peer_groups_df = load_peer_groups()

    with sqlite3.connect(DATABASE_PATH) as connection:

        year = get_latest_annual_year(
            connection
        )

        peer_percentiles_df = (
            load_peer_percentile_data(
                connection,
                year,
            )
        )

        composite_scores_df = (
            load_composite_scores(
                connection,
                year,
            )
        )

    radar_df = build_radar_dataset(
        peer_percentiles_df,
        composite_scores_df,
    )

    return (
        peer_groups_df,
        peer_percentiles_df,
        composite_scores_df,
        radar_df,
        year,
    )


@st.cache_data
def load_peer_kpi_data(year: str):
    """
    Load KPI metrics for the peer comparison table.
    """

    query = """
        SELECT
            r.company_id,
            r.return_on_equity_pct,
            r.return_on_capital_employed_pct,
            r.net_profit_margin_pct,
            r.debt_to_equity,
            r.free_cash_flow_cr,
            r.pat_cagr_5yr,
            r.revenue_cagr_5yr,
            r.composite_quality_score,

            c.company_name

        FROM financial_ratios r

        LEFT JOIN companies c
            ON UPPER(TRIM(r.company_id))
             = UPPER(TRIM(c.id))

        WHERE r.year = ?
    """

    with sqlite3.connect(
        DATABASE_PATH
    ) as connection:

        dataframe = pd.read_sql_query(
            query,
            connection,
            params=(year,),
        )

    dataframe["company_id"] = (
        dataframe["company_id"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    return dataframe


# --------------------------------------------------
# Formatting
# --------------------------------------------------

def format_number(value, decimals=2):
    """Format numeric values safely."""

    if pd.isna(value):
        return "-"

    return f"{value:,.{decimals}f}"


def build_kpi_table(
    peer_groups_df,
    selected_group,
    selected_company,
    year,
):
    """
    Build KPI table for all companies
    in the selected peer group.
    """

    kpi_df = load_peer_kpi_data(year).copy()

    peer_mapping = peer_groups_df.copy()

    peer_mapping["company_id"] = (
        peer_mapping["company_id"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    group_companies = peer_mapping[
        peer_mapping["peer_group_name"]
        == selected_group
    ].copy()

    group_df = group_companies.merge(
        kpi_df,
        on="company_id",
        how="left",
    )

    display_columns = [
        "company_id",
        "company_name",
        "return_on_equity_pct",
        "return_on_capital_employed_pct",
        "net_profit_margin_pct",
        "debt_to_equity",
        "free_cash_flow_cr",
        "pat_cagr_5yr",
        "revenue_cagr_5yr",
        "composite_quality_score",
    ]

    display_columns = [
        column
        for column in display_columns
        if column in group_df.columns
    ]

    result = group_df[
        display_columns
    ].copy()

    result = result.rename(
        columns={
            "company_id": "Company ID",
            "company_name": "Company Name",
            "return_on_equity_pct": "ROE %",
            "return_on_capital_employed_pct": "ROCE %",
            "net_profit_margin_pct": "NPM %",
            "debt_to_equity": "Debt / Equity",
            "free_cash_flow_cr": "FCF (Cr)",
            "pat_cagr_5yr": "PAT CAGR 5Y %",
            "revenue_cagr_5yr": "Revenue CAGR 5Y %",
            "composite_quality_score": "Composite Score",
        }
    )

    result = result.sort_values(
        by="Composite Score",
        ascending=False,
        na_position="last",
    )

    return result


def highlight_benchmark(
    dataframe,
    benchmark_company,
):
    """
    Highlight the selected benchmark company row.
    """

    def highlight_row(row):

        if row["Company ID"] == benchmark_company:

            return [
                (
                    "background-color: "
                    "rgba(46, 204, 113, 0.25); "
                    "font-weight: bold;"
                )
            ] * len(row)

        return [""] * len(row)

    return dataframe.style.apply(
        highlight_row,
        axis=1,
    )


# --------------------------------------------------
# Plotly Radar Chart
# --------------------------------------------------

def create_peer_radar_chart(
    selected_company,
    selected_group,
    radar_df,
):
    """
    Create an 8-axis Plotly radar chart.

    Selected company vs peer group average.
    """

    company_row = radar_df[
        (
            radar_df["company_id"]
            == selected_company
        )
        &
        (
            radar_df["peer_group_name"]
            == selected_group
        )
    ]

    if company_row.empty:
        return None

    company_row = company_row.iloc[0]

    company_values = []

    for axis in AXES:

        value = company_row[axis]

        if pd.isna(value):
            value = 0.0

        company_values.append(
            float(value)
        )

    peer_average_values = (
        get_peer_group_average(
            radar_df,
            selected_group,
        )
    )

    # Close radar polygons.
    theta = AXES + [AXES[0]]

    company_r = (
        company_values
        + [company_values[0]]
    )

    peer_r = (
        peer_average_values
        + [peer_average_values[0]]
    )

    figure = go.Figure()

    # Selected company
    figure.add_trace(
        go.Scatterpolar(
            r=company_r,
            theta=theta,
            fill="toself",
            name=selected_company,
            hovertemplate=(
                "<b>%{theta}</b><br>"
                "Relative Score: %{r:.2f}"
                "<extra></extra>"
            ),
        )
    )

    # Peer average
    figure.add_trace(
        go.Scatterpolar(
            r=peer_r,
            theta=theta,
            fill="none",
            name="Peer Group Average",
            line={
                "dash": "dash",
            },
            hovertemplate=(
                "<b>%{theta}</b><br>"
                "Peer Average: %{r:.2f}"
                "<extra></extra>"
            ),
        )
    )

    figure.update_layout(
        title=(
            f"{selected_company} vs "
            f"{selected_group} Peer Average"
        ),
        polar={
            "radialaxis": {
                "visible": True,
                "range": [0, 1],
                "tickvals": [
                    0.2,
                    0.4,
                    0.6,
                    0.8,
                    1.0,
                ],
            },
        },
        showlegend=True,
        height=600,
        margin={
            "l": 60,
            "r": 60,
            "t": 80,
            "b": 60,
        },
    )

    return figure


# --------------------------------------------------
# Page
# --------------------------------------------------

def render():

    st.title("👥 Peer Comparison")

    st.caption(
        "Compare companies within their peer groups "
        "using relative financial performance metrics."
    )

    # --------------------------------------------------
    # Load data
    # --------------------------------------------------

    try:

        (
            peer_groups_df,
            peer_percentiles_df,
            composite_scores_df,
            radar_df,
            year,
        ) = load_peer_dashboard_data()

    except Exception as error:

        st.error(
            "Unable to load peer comparison data: "
            f"{error}"
        )

        st.info(
            "Make sure Day 18 peer percentile "
            "rankings have been generated."
        )

        return

    if peer_groups_df.empty:

        st.warning(
            "No peer group data is available."
        )

        return

    if radar_df.empty:

        st.warning(
            "No radar comparison data is available."
        )

        return

    # --------------------------------------------------
    # Peer group dropdown
    # --------------------------------------------------

    peer_groups = sorted(
        peer_groups_df[
            "peer_group_name"
        ]
        .dropna()
        .unique()
        .tolist()
    )

    st.subheader("Peer Group Selection")

    selected_group = st.selectbox(
        "Select Peer Group",
        options=peer_groups,
    )

    # --------------------------------------------------
    # Companies in selected peer group
    # --------------------------------------------------

    group_companies = radar_df[
        radar_df["peer_group_name"]
        == selected_group
    ].copy()

    company_options = sorted(
        group_companies[
            "company_id"
        ]
        .dropna()
        .unique()
        .tolist()
    )

    if not company_options:

        st.warning(
            "No companies are available "
            "for this peer group."
        )

        return

    selected_company = st.selectbox(
        "Select Benchmark Company",
        options=company_options,
    )

    st.caption(
        f"Financial Year: {year}"
    )

    st.markdown("---")

    # --------------------------------------------------
    # KPI summary
    # --------------------------------------------------

    total_companies = len(
        company_options
    )

    col1, col2, col3 = st.columns(3)

    with col1:

        st.metric(
            "Peer Group",
            selected_group,
        )

    with col2:

        st.metric(
            "Companies in Group",
            total_companies,
        )

    with col3:

        st.metric(
            "Benchmark Company",
            selected_company,
        )

    # --------------------------------------------------
    # Radar chart
    # --------------------------------------------------

    st.subheader(
        "8-Metric Relative Performance"
    )

    st.caption(
        "Scores are normalised from 0 to 1 "
        "within the selected peer group. "
        "Higher scores represent stronger "
        "relative performance."
    )

    radar_chart = (
        create_peer_radar_chart(
            selected_company,
            selected_group,
            radar_df,
        )
    )

    if radar_chart is not None:

        st.plotly_chart(
            radar_chart,
            use_container_width=True,
        )

    else:

        st.warning(
            "Radar data is unavailable "
            "for the selected company."
        )

    # --------------------------------------------------
    # KPI comparison table
    # --------------------------------------------------

    st.markdown("---")

    st.subheader(
        "Peer Group KPI Comparison"
    )

    st.caption(
        "The benchmark company is highlighted."
    )

    try:

        kpi_table = build_kpi_table(
            peer_groups_df,
            selected_group,
            selected_company,
            year,
        )

    except Exception as error:

        st.error(
            "Unable to load peer KPI table: "
            f"{error}"
        )

        return

    if kpi_table.empty:

        st.warning(
            "No KPI data is available "
            "for this peer group."
        )

        return

    styled_table = highlight_benchmark(
        kpi_table,
        selected_company,
    )

    st.dataframe(
        styled_table,
        use_container_width=True,
        hide_index=True,
    )

    # --------------------------------------------------
    # Benchmark note
    # --------------------------------------------------

    st.info(
        f"Benchmark: {selected_company} "
        f"| Peer Group: {selected_group} "
        f"| Companies Compared: {total_companies}"
    )