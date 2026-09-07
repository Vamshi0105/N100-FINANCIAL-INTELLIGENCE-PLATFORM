from pathlib import Path
import sqlite3

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATABASE_PATH = PROJECT_ROOT / "data" / "nifty100.db"


METRICS = {
    "Revenue": "sales",
    "Net Profit": "net_profit",
    "ROE %": "return_on_equity_pct",
    "ROCE %": "return_on_capital_employed_pct",
    "Net Profit Margin %": "net_profit_margin_pct",
    "Operating Profit Margin %": "operating_profit_margin_pct",
    "Free Cash Flow (Cr)": "free_cash_flow_cr",
    "Debt / Equity": "debt_to_equity",
    "PAT CAGR 5Y %": "pat_cagr_5yr",
    "Revenue CAGR 5Y %": "revenue_cagr_5yr",
}


@st.cache_data
def load_companies():
    """
    Load companies for the searchable company selector.
    """

    connection = sqlite3.connect(DATABASE_PATH)

    query = """
        SELECT
            id AS company_id,
            company_name
        FROM companies
        ORDER BY company_name
    """

    dataframe = pd.read_sql_query(
        query,
        connection,
    )

    connection.close()

    return dataframe


@st.cache_data
def load_company_trends(company_id):
    """
    Load annual historical financial data for one company.
    """

    connection = sqlite3.connect(DATABASE_PATH)

    query = """
        SELECT
            r.company_id,
            r.year,

            p.sales,
            p.net_profit,

            r.return_on_equity_pct,
            r.return_on_capital_employed_pct,
            r.net_profit_margin_pct,
            r.operating_profit_margin_pct,
            r.free_cash_flow_cr,
            r.debt_to_equity,
            r.pat_cagr_5yr,
            r.revenue_cagr_5yr

        FROM financial_ratios r

        LEFT JOIN profitandloss p
            ON r.company_id = p.company_id
            AND r.year = p.year

        WHERE r.company_id = ?
            AND r.year LIKE '%-03'

        ORDER BY r.year
    """

    dataframe = pd.read_sql_query(
        query,
        connection,
        params=(company_id,),
    )

    connection.close()

    return dataframe


def calculate_yoy_change(values):
    """
    Calculate Year-over-Year percentage change.

    Formula:
        ((current - previous) / abs(previous)) * 100

    First year returns None.
    """

    changes = []

    previous_value = None

    for value in values:

        if (
            previous_value is None
            or pd.isna(previous_value)
            or pd.isna(value)
            or previous_value == 0
        ):
            changes.append(None)

        else:

            yoy_change = (
                (value - previous_value)
                / abs(previous_value)
            ) * 100

            changes.append(
                round(yoy_change, 1)
            )

        previous_value = value

    return changes


def create_trend_chart(
    dataframe,
    selected_metrics,
):
    """
    Create a multi-metric financial trend chart.

    Supports overlaying up to 3 metrics.
    Each data point displays YoY percentage change.
    """

    figure = go.Figure()

    for metric_name in selected_metrics:

        column = METRICS[metric_name]

        if column not in dataframe.columns:
            continue

        metric_dataframe = dataframe[
            ["year", column]
        ].copy()

        metric_dataframe = metric_dataframe.dropna()

        if metric_dataframe.empty:
            continue

        yoy_changes = calculate_yoy_change(
            metric_dataframe[column].tolist()
        )

        text_labels = []

        for change in yoy_changes:

            if change is None:
                text_labels.append("")

            else:
                text_labels.append(
                    f"{change:+.1f}%"
                )

        figure.add_trace(
            go.Scatter(
                x=metric_dataframe["year"],
                y=metric_dataframe[column],
                mode="lines+markers+text",
                name=metric_name,
                text=text_labels,
                textposition="top center",
                hovertemplate=(
                    "<b>%{x}</b><br>"
                    f"{metric_name}: "
                    "%{y:,.2f}<br>"
                    "<extra></extra>"
                ),
                marker=dict(
                    size=9,
                ),
                line=dict(
                    width=3,
                ),
            )
        )

    figure.update_layout(
        title="10-Year Financial Trend",
        height=600,
        hovermode="x unified",
        xaxis_title="Financial Year",
        yaxis_title="Metric Value",
        legend_title="Metrics",
        margin=dict(
            l=40,
            r=40,
            t=80,
            b=40,
        ),
    )

    figure.update_xaxes(
        tickangle=-45,
    )

    return figure


def render():

    st.title("📈 Financial Trends")

    st.caption(
        "Analyse long-term financial performance "
        "and year-over-year changes."
    )

    # -------------------------------------------------
    # LOAD COMPANIES
    # -------------------------------------------------

    companies_dataframe = load_companies()

    if companies_dataframe.empty:

        st.error(
            "No companies were found in the database."
        )

        return

    # -------------------------------------------------
    # COMPANY SEARCH
    # -------------------------------------------------

    st.subheader("Company Selection")

    company_options = (
        companies_dataframe
        .apply(
            lambda row:
            f"{row['company_id']} — {row['company_name']}",
            axis=1,
        )
        .tolist()
    )

    selected_company_display = st.selectbox(
        "Search and select a company",
        options=company_options,
        index=0,
    )

    selected_company_id = (
        selected_company_display
        .split(" — ")[0]
    )

    # -------------------------------------------------
    # METRIC SELECTOR
    # -------------------------------------------------

    st.subheader("Metric Selection")

    selected_metrics = st.multiselect(
        "Select up to 3 metrics to overlay",
        options=list(METRICS.keys()),
        default=[
            "Revenue",
            "Net Profit",
        ],
        max_selections=3,
    )

    if not selected_metrics:

        st.warning(
            "Please select at least one metric."
        )

        return

    # -------------------------------------------------
    # LOAD COMPANY DATA
    # -------------------------------------------------

    trends_dataframe = load_company_trends(
        selected_company_id
    )

    if trends_dataframe.empty:

        st.warning(
            f"No annual financial trend data found "
            f"for {selected_company_id}."
        )

        return

    # -------------------------------------------------
    # KEEP MOST RECENT 10 YEARS
    # -------------------------------------------------

    trends_dataframe = (
        trends_dataframe
        .sort_values("year")
        .tail(10)
        .reset_index(drop=True)
    )

    # -------------------------------------------------
    # COMPANY SUMMARY
    # -------------------------------------------------

    selected_company_name = (
        companies_dataframe[
            companies_dataframe["company_id"]
            .astype(str)
            == selected_company_id
        ]["company_name"]
        .iloc[0]
    )

    latest_year = trends_dataframe[
        "year"
    ].iloc[-1]

    oldest_year = trends_dataframe[
        "year"
    ].iloc[0]

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Company",
        selected_company_id,
    )

    col2.metric(
        "Historical Period",
        f"{oldest_year} to {latest_year}",
    )

    col3.metric(
        "Metrics Selected",
        len(selected_metrics),
    )

    st.divider()

    # -------------------------------------------------
    # TREND CHART
    # -------------------------------------------------

    st.subheader(
        f"{selected_company_name} — Financial Trends"
    )

    trend_chart = create_trend_chart(
        trends_dataframe,
        selected_metrics,
    )

    st.plotly_chart(
        trend_chart,
        use_container_width=True,
    )

    # -------------------------------------------------
    # DATA TABLE
    # -------------------------------------------------

    st.subheader("Historical Data")

    display_columns = [
        "year",
    ]

    for metric_name in selected_metrics:

        column = METRICS[metric_name]

        if column in trends_dataframe.columns:
            display_columns.append(column)

    display_dataframe = trends_dataframe[
        display_columns
    ].copy()

    rename_columns = {
        "year": "Financial Year",
    }

    for metric_name in selected_metrics:

        column = METRICS[metric_name]

        rename_columns[column] = metric_name

    display_dataframe = display_dataframe.rename(
        columns=rename_columns
    )

    st.dataframe(
        display_dataframe,
        use_container_width=True,
        hide_index=True,
    )