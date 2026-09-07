from pathlib import Path
import sqlite3

import pandas as pd
import plotly.express as px
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATABASE_PATH = PROJECT_ROOT / "data" / "nifty100.db"


@st.cache_data
def load_sector_data():
    """
    Load the latest annual financial data together with
    sector, company and market-cap information.
    """

    connection = sqlite3.connect(DATABASE_PATH)

    query = """
    WITH latest_annual AS (
        SELECT
            company_id,
            MAX(year) AS latest_year
        FROM financial_ratios
        WHERE year LIKE '%-03'
        GROUP BY company_id
    )

    SELECT
        r.company_id,
        c.company_name,

        r.year,

        s.broad_sector,
        s.sub_sector,

        p.sales AS revenue,
        p.net_profit,

        r.return_on_equity_pct,
        r.return_on_capital_employed_pct,
        r.operating_profit_margin_pct,
        r.net_profit_margin_pct,
        r.free_cash_flow_cr,
        r.composite_quality_score,

        m.market_cap_crore

    FROM financial_ratios r

    INNER JOIN latest_annual la
        ON r.company_id = la.company_id
        AND r.year = la.latest_year

    LEFT JOIN companies c
        ON r.company_id = c.id

    LEFT JOIN sectors s
        ON r.company_id = s.company_id

    LEFT JOIN profitandloss p
        ON r.company_id = p.company_id
        AND r.year = p.year

    LEFT JOIN market_cap m
        ON r.company_id = m.company_id
        AND CAST(SUBSTR(r.year, 1, 4) AS INTEGER) = m.year
    """

    dataframe = pd.read_sql_query(query, connection)

    connection.close()

    dataframe["company_id"] = (
        dataframe["company_id"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    dataframe["company_name"] = (
        dataframe["company_name"]
        .fillna(dataframe["company_id"])
        .astype(str)
    )

    dataframe["broad_sector"] = (
        dataframe["broad_sector"]
        .fillna("Unknown")
        .astype(str)
    )

    dataframe["sub_sector"] = (
        dataframe["sub_sector"]
        .fillna("Unknown")
        .astype(str)
    )

    numeric_columns = [
        "revenue",
        "net_profit",
        "return_on_equity_pct",
        "return_on_capital_employed_pct",
        "operating_profit_margin_pct",
        "net_profit_margin_pct",
        "free_cash_flow_cr",
        "composite_quality_score",
        "market_cap_crore",
    ]

    for column in numeric_columns:
        dataframe[column] = pd.to_numeric(
            dataframe[column],
            errors="coerce",
        )

    return dataframe


def render():

    st.title("🏭 Sector Analysis")

    st.write(
        "Compare companies within each sector using revenue, "
        "profitability and market capitalisation."
    )

    dataframe = load_sector_data()

    if dataframe.empty:
        st.warning("No sector data is available.")
        return

    # -------------------------------------------------
    # Sector Selection
    # -------------------------------------------------

    st.subheader("Sector Selection")

    sectors = sorted(
        dataframe["broad_sector"]
        .dropna()
        .unique()
        .tolist()
    )

    selected_sector = st.selectbox(
        "Select Sector",
        sectors,
    )

    sector_df = dataframe[
        dataframe["broad_sector"]
        == selected_sector
    ].copy()

    if sector_df.empty:
        st.warning(
            "No companies are available for the selected sector."
        )
        return

    # -------------------------------------------------
    # Summary KPIs
    # -------------------------------------------------

    company_count = len(sector_df)

    median_revenue = (
        sector_df["revenue"]
        .median()
    )

    median_roe = (
        sector_df["return_on_equity_pct"]
        .median()
    )

    median_market_cap = (
        sector_df["market_cap_crore"]
        .median()
    )

    latest_year = (
        sector_df["year"]
        .dropna()
        .max()
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Companies",
        company_count,
    )

    col2.metric(
        "Median Revenue",
        (
            f"₹{median_revenue:,.0f} Cr"
            if pd.notna(median_revenue)
            else "N/A"
        ),
    )

    col3.metric(
        "Median ROE",
        (
            f"{median_roe:.2f}%"
            if pd.notna(median_roe)
            else "N/A"
        ),
    )

    col4.metric(
        "Median Market Cap",
        (
            f"₹{median_market_cap:,.0f} Cr"
            if pd.notna(median_market_cap)
            else "N/A"
        ),
    )

    st.divider()

    # -------------------------------------------------
    # Bubble Chart
    # -------------------------------------------------

    st.subheader(
        f"{selected_sector} — Company Positioning"
    )

    st.caption(
        "Bubble size represents market capitalisation. "
        "Colour represents sub-sector."
    )

    bubble_df = sector_df.dropna(
        subset=[
            "revenue",
            "return_on_equity_pct",
            "market_cap_crore",
        ]
    ).copy()

    if bubble_df.empty:

        st.info(
            "Insufficient data is available to create "
            "the bubble chart."
        )

    else:

        # Avoid zero/negative bubble sizes.
        bubble_df["bubble_size"] = (
            bubble_df["market_cap_crore"]
            .clip(lower=1)
        )

        figure = px.scatter(
            bubble_df,
            x="revenue",
            y="return_on_equity_pct",
            size="bubble_size",
            color="sub_sector",
            hover_name="company_name",
            hover_data={
                "company_id": True,
                "revenue": ":,.2f",
                "return_on_equity_pct": ":.2f",
                "market_cap_crore": ":,.2f",
                "bubble_size": False,
                "sub_sector": True,
            },
            size_max=65,
            labels={
                "revenue": "Revenue (₹ Cr)",
                "return_on_equity_pct": "ROE (%)",
                "sub_sector": "Sub-Sector",
                "market_cap_crore": "Market Cap (₹ Cr)",
            },
        )

        figure.update_layout(
            height=650,
            xaxis_title="Revenue (₹ Crore)",
            yaxis_title="Return on Equity — ROE (%)",
            legend_title="Sub-Sector",
        )

        st.plotly_chart(
            figure,
            use_container_width=True,
        )

    st.divider()

    # -------------------------------------------------
    # Sector Median KPI Bar Chart
    # -------------------------------------------------

    st.subheader(
        f"{selected_sector} — Median Financial KPIs"
    )

    median_kpis = pd.DataFrame(
        {
            "Metric": [
                "ROE %",
                "ROCE %",
                "OPM %",
                "Net Profit Margin %",
                "Composite Score",
            ],
            "Median Value": [
                sector_df[
                    "return_on_equity_pct"
                ].median(),

                sector_df[
                    "return_on_capital_employed_pct"
                ].median(),

                sector_df[
                    "operating_profit_margin_pct"
                ].median(),

                sector_df[
                    "net_profit_margin_pct"
                ].median(),

                sector_df[
                    "composite_quality_score"
                ].median(),
            ],
        }
    )

    median_kpis = median_kpis.dropna(
        subset=["Median Value"]
    )

    if median_kpis.empty:

        st.info(
            "Insufficient data is available to calculate "
            "sector median KPIs."
        )

    else:

        median_figure = px.bar(
            median_kpis,
            x="Metric",
            y="Median Value",
            text_auto=".2f",
            labels={
                "Metric": "Financial Metric",
                "Median Value": "Sector Median",
            },
        )

        median_figure.update_layout(
            height=500,
            showlegend=False,
            yaxis_title="Median Value",
            xaxis_title="",
        )

        st.plotly_chart(
            median_figure,
            use_container_width=True,
        )

    # -------------------------------------------------
    # Company Data Table
    # -------------------------------------------------

    st.divider()

    st.subheader(
        f"{selected_sector} — Company Data"
    )

    display_columns = [
        "company_id",
        "company_name",
        "sub_sector",
        "revenue",
        "return_on_equity_pct",
        "return_on_capital_employed_pct",
        "operating_profit_margin_pct",
        "net_profit_margin_pct",
        "market_cap_crore",
        "composite_quality_score",
    ]

    available_columns = [
        column
        for column in display_columns
        if column in sector_df.columns
    ]

    display_df = (
        sector_df[available_columns]
        .sort_values(
            by="market_cap_crore",
            ascending=False,
            na_position="last",
        )
        .reset_index(drop=True)
    )

    display_df = display_df.rename(
        columns={
            "company_id": "Company ID",
            "company_name": "Company",
            "sub_sector": "Sub-Sector",
            "revenue": "Revenue (₹ Cr)",
            "return_on_equity_pct": "ROE %",
            "return_on_capital_employed_pct": "ROCE %",
            "operating_profit_margin_pct": "OPM %",
            "net_profit_margin_pct": "NPM %",
            "market_cap_crore": "Market Cap (₹ Cr)",
            "composite_quality_score": "Composite Score",
        }
    )

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
    )

    st.caption(
        f"Financial period: {latest_year} | "
        f"{company_count} companies in {selected_sector}"
    )