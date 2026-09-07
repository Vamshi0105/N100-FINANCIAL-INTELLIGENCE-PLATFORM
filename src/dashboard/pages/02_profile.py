import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from src.dashboard.utils.db import (
    get_companies,
    get_company_profile,
    get_ratios,
    get_pl,
    get_pros_cons,
)


# ---------------------------------------------------------
# SAFE DISPLAY HELPERS
# ---------------------------------------------------------

def safe_text(value, default="N/A"):
    """
    Safely convert missing text values to a display value.
    """

    if value is None:
        return default

    try:
        if pd.isna(value):
            return default
    except (ValueError, TypeError):
        pass

    value = str(value).strip()

    if not value:
        return default

    return value


def format_number(value, suffix="", decimals=2):
    """
    Safely format numeric values.

    Missing values are displayed as N/A.
    """

    if value is None:
        return "N/A"

    try:
        if pd.isna(value):
            return "N/A"

        return f"{float(value):,.{decimals}f}{suffix}"

    except (ValueError, TypeError):
        return "N/A"


def format_currency_cr(value):
    """
    Format a financial value in ₹ Crore.

    Missing values are displayed as N/A.
    """

    if value is None:
        return "N/A"

    try:
        if pd.isna(value):
            return "N/A"

        value = float(value)

        if abs(value) >= 1000:
            return f"₹{value:,.0f} Cr"

        return f"₹{value:,.2f} Cr"

    except (ValueError, TypeError):
        return "N/A"


def get_annual_record_count(dataframe):
    """
    Count unique annual March year-end records.

    Annual records use the format YYYY-03.
    """

    if dataframe.empty:
        return 0

    if "year" not in dataframe.columns:
        return 0

    years = dataframe["year"].astype(str)

    annual_years = years[
        years.str.endswith("-03")
    ]

    return annual_years.nunique()


def render():

    # ---------------------------------------------------------
    # PAGE TITLE
    # ---------------------------------------------------------

    st.title("🏢 Company Profile")

    # ---------------------------------------------------------
    # LOAD COMPANY LIST
    # ---------------------------------------------------------

    companies = get_companies()

    if companies.empty:
        st.error("Company data is not available.")
        return

    # ---------------------------------------------------------
    # COMPANY SEARCH / AUTOCOMPLETE
    # ---------------------------------------------------------

    search_text = st.text_input(
        "🔍 Search company by ticker or company name",
        placeholder="Example: TCS or Tata Consultancy Services",
    )

    company_options = companies.copy()

    if search_text:

        search_mask = (
            company_options["company_id"]
            .astype(str)
            .str.contains(
                search_text,
                case=False,
                na=False,
            )
            |
            company_options["company_name"]
            .astype(str)
            .str.contains(
                search_text,
                case=False,
                na=False,
            )
        )

        company_options = company_options[
            search_mask
        ]

    if company_options.empty:
        st.warning(
            "Ticker not found — please try another."
        )
        return

    # ---------------------------------------------------------
    # COMPANY SELECTOR
    # ---------------------------------------------------------

    company_options = company_options.copy()

    company_options["display_name"] = (
        company_options["company_id"]
        .astype(str)
        + " — "
        + company_options["company_name"]
        .astype(str)
    )

    selected_company = st.selectbox(
        "Select Company",
        company_options["display_name"].tolist(),
    )

    ticker = selected_company.split(
        " — "
    )[0]

    # ---------------------------------------------------------
    # COMPANY PROFILE
    # ---------------------------------------------------------

    profile = get_company_profile(
        ticker
    )

    if profile.empty:
        st.warning(
            "Ticker not found — please try another."
        )
        return

    profile_row = profile.iloc[0]

    company_name = safe_text(
        profile_row.get("company_name"),
        ticker,
    )

    broad_sector = safe_text(
        profile_row.get("broad_sector"),
        "N/A",
    )

    sub_sector = safe_text(
        profile_row.get("sub_sector"),
        "N/A",
    )

    about_company = safe_text(
        profile_row.get("about_company"),
        "Description not available.",
    )

    # ---------------------------------------------------------
    # COMPANY CARD
    # ---------------------------------------------------------

    st.markdown("---")

    st.subheader(
        company_name
    )

    col1, col2, col3 = st.columns(3)

    with col1:

        st.write(
            "**NSE Ticker**"
        )

        st.write(
            ticker
        )

    with col2:

        st.write(
            "**Sector**"
        )

        st.write(
            broad_sector
        )

    with col3:

        st.write(
            "**Sub-Sector**"
        )

        st.write(
            sub_sector
        )

    st.markdown(
        "### About Company"
    )

    st.write(
        about_company
    )

    st.markdown("---")

    # ---------------------------------------------------------
    # LOAD FINANCIAL DATA
    # ---------------------------------------------------------

    ratios = get_ratios(
        ticker
    )

    pl = get_pl(
        ticker
    )

    # ---------------------------------------------------------
    # PARTIAL DATA WARNING
    # ---------------------------------------------------------

    annual_record_count = (
        get_annual_record_count(
            ratios
        )
    )

    if annual_record_count < 10:

        st.info(
            f"📊 Data available for "
            f"{annual_record_count} annual year(s). "
            "Some long-term metrics and charts may "
            "have limited history."
        )

    # ---------------------------------------------------------
    # FIND LATEST COMPLETE FINANCIAL RECORD
    # ---------------------------------------------------------

    latest_ratios = None

    if not ratios.empty:

        ratios = ratios.copy()

        ratios["year"] = (
            ratios["year"]
            .astype(str)
        )

        complete_ratios = ratios[
            ratios[
                "return_on_equity_pct"
            ].notna()
            &
            ratios[
                "return_on_capital_employed_pct"
            ].notna()
            &
            ratios[
                "net_profit_margin_pct"
            ].notna()
        ].copy()

        complete_ratios = (
            complete_ratios
            .sort_values(
                "year",
                ascending=True,
            )
        )

        if not complete_ratios.empty:

            latest_ratios = (
                complete_ratios
                .iloc[-1]
            )

    # ---------------------------------------------------------
    # KPI TILES
    # ---------------------------------------------------------

    st.subheader(
        "Key Financial Metrics"
    )

    (
        kpi1,
        kpi2,
        kpi3,
        kpi4,
        kpi5,
        kpi6,
    ) = st.columns(6)

    if latest_ratios is not None:

        roe = latest_ratios.get(
            "return_on_equity_pct"
        )

        roce = latest_ratios.get(
            "return_on_capital_employed_pct"
        )

        npm = latest_ratios.get(
            "net_profit_margin_pct"
        )

        debt_equity = latest_ratios.get(
            "debt_to_equity"
        )

        revenue_cagr = latest_ratios.get(
            "revenue_cagr_5yr"
        )

        fcf = latest_ratios.get(
            "free_cash_flow_cr"
        )

    else:

        roe = None
        roce = None
        npm = None
        debt_equity = None
        revenue_cagr = None
        fcf = None

    kpi1.metric(
        "ROE",
        format_number(
            roe,
            "%",
        ),
    )

    kpi2.metric(
        "ROCE",
        format_number(
            roce,
            "%",
        ),
    )

    kpi3.metric(
        "Net Profit Margin",
        format_number(
            npm,
            "%",
        ),
    )

    kpi4.metric(
        "Debt / Equity",
        format_number(
            debt_equity,
        ),
    )

    kpi5.metric(
        "Revenue CAGR 5Y",
        format_number(
            revenue_cagr,
            "%",
        ),
    )

    kpi6.metric(
        "Free Cash Flow",
        format_currency_cr(
            fcf
        ),
    )

    st.markdown("---")

    # ---------------------------------------------------------
    # REVENUE AND NET PROFIT CHART
    # ---------------------------------------------------------

    st.subheader(
        "Revenue & Net Profit Trend"
    )

    if pl.empty:

        st.info(
            "Profit & Loss data is not available."
        )

    else:

        pl_chart = pl.copy()

        pl_chart["year"] = (
            pl_chart["year"]
            .astype(str)
        )

        available_columns = []

        if "sales" in pl_chart.columns:
            available_columns.append(
                "sales"
            )

        if "net_profit" in pl_chart.columns:
            available_columns.append(
                "net_profit"
            )

        if available_columns:

            pl_chart = (
                pl_chart
                .dropna(
                    subset=available_columns,
                    how="all",
                )
            )

        pl_chart = (
            pl_chart
            .sort_values(
                "year"
            )
        )

        if pl_chart.empty:

            st.info(
                "Revenue and Net Profit data "
                "is not available."
            )

        else:

            fig = go.Figure()

            # ---------------------------------------------
            # REVENUE
            # ---------------------------------------------

            if "sales" in pl_chart.columns:

                fig.add_trace(
                    go.Bar(
                        x=pl_chart["year"],
                        y=pl_chart["sales"],
                        name="Revenue",
                        hovertemplate=(
                            "<b>Year:</b> %{x}<br>"
                            "<b>Revenue:</b> "
                            "₹%{y:,.0f} Cr"
                            "<extra></extra>"
                        ),
                    )
                )

            # ---------------------------------------------
            # NET PROFIT
            # ---------------------------------------------

            if "net_profit" in pl_chart.columns:

                fig.add_trace(
                    go.Scatter(
                        x=pl_chart["year"],
                        y=pl_chart[
                            "net_profit"
                        ],
                        mode="lines+markers",
                        name="Net Profit",
                        yaxis="y2",
                        hovertemplate=(
                            "<b>Year:</b> %{x}<br>"
                            "<b>Net Profit:</b> "
                            "₹%{y:,.0f} Cr"
                            "<extra></extra>"
                        ),
                    )
                )

            fig.update_layout(

                height=500,

                hovermode="x unified",

                xaxis=dict(
                    title="Financial Year",
                ),

                yaxis=dict(
                    title="Revenue (₹ Cr)",
                    rangemode="tozero",
                ),

                yaxis2=dict(
                    title="Net Profit (₹ Cr)",
                    overlaying="y",
                    side="right",
                    rangemode="tozero",
                ),

                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1,
                ),

                margin=dict(
                    l=60,
                    r=60,
                    t=60,
                    b=60,
                ),
            )

            st.plotly_chart(
                fig,
                use_container_width=True,
            )

    # ---------------------------------------------------------
    # PROS AND CONS
    # ---------------------------------------------------------

    st.markdown("---")

    st.subheader(
        "Pros & Cons"
    )

    pros_cons = get_pros_cons(
        ticker
    )

    pros_column, cons_column = (
        st.columns(2)
    )

    # ---------------------------------------------------------
    # PROS
    # ---------------------------------------------------------

    with pros_column:

        st.markdown(
            "### ✅ Pros"
        )

        if not pros_cons.empty and "pros" in pros_cons.columns:

            pros_values = (
                pros_cons["pros"]
                .dropna()
                .astype(str)
                .tolist()
            )

            if pros_values:

                for pro in pros_values:

                    st.success(
                        f"✓ {pro}"
                    )

            else:

                st.info(
                    "No pros data available."
                )

        else:

            st.info(
                "No pros data available."
            )

    # ---------------------------------------------------------
    # CONS
    # ---------------------------------------------------------

    with cons_column:

        st.markdown(
            "### ❌ Cons"
        )

        if not pros_cons.empty and "cons" in pros_cons.columns:

            cons_values = (
                pros_cons["cons"]
                .dropna()
                .astype(str)
                .tolist()
            )

            if cons_values:

                for con in cons_values:

                    st.error(
                        f"✗ {con}"
                    )

            else:

                st.info(
                    "No cons data available."
                )

        else:

            st.info(
                "No cons data available."
            )

    # ---------------------------------------------------------
    # ROE AND ROCE TREND
    # ---------------------------------------------------------

    st.markdown("---")

    st.subheader(
        "ROE & ROCE Trend"
    )

    if ratios.empty:

        st.info(
            "Financial ratio history "
            "is not available."
        )

    else:

        ratios_chart = (
            ratios.copy()
        )

        ratio_columns = []

        if (
            "return_on_equity_pct"
            in ratios_chart.columns
        ):
            ratio_columns.append(
                "return_on_equity_pct"
            )

        if (
            "return_on_capital_employed_pct"
            in ratios_chart.columns
        ):
            ratio_columns.append(
                "return_on_capital_employed_pct"
            )

        if ratio_columns:

            ratios_chart = (
                ratios_chart
                .dropna(
                    subset=ratio_columns,
                    how="all",
                )
            )

        ratios_chart["year"] = (
            ratios_chart["year"]
            .astype(str)
        )

        ratios_chart = (
            ratios_chart
            .sort_values(
                "year"
            )
        )

        if ratios_chart.empty:

            st.info(
                "ROE and ROCE data is "
                "not available."
            )

        else:

            fig = go.Figure()

            # ---------------------------------------------
            # ROE
            # ---------------------------------------------

            if (
                "return_on_equity_pct"
                in ratios_chart.columns
                and
                ratios_chart[
                    "return_on_equity_pct"
                ].notna().any()
            ):

                fig.add_trace(
                    go.Scatter(
                        x=ratios_chart[
                            "year"
                        ],
                        y=ratios_chart[
                            "return_on_equity_pct"
                        ],
                        mode="lines+markers",
                        name="ROE",
                        hovertemplate=(
                            "<b>Year:</b> %{x}<br>"
                            "<b>ROE:</b> "
                            "%{y:.2f}%"
                            "<extra></extra>"
                        ),
                    )
                )

            # ---------------------------------------------
            # ROCE
            # ---------------------------------------------

            if (
                "return_on_capital_employed_pct"
                in ratios_chart.columns
                and
                ratios_chart[
                    "return_on_capital_employed_pct"
                ].notna().any()
            ):

                fig.add_trace(
                    go.Scatter(
                        x=ratios_chart[
                            "year"
                        ],
                        y=ratios_chart[
                            "return_on_capital_employed_pct"
                        ],
                        mode="lines+markers",
                        name="ROCE",
                        hovertemplate=(
                            "<b>Year:</b> %{x}<br>"
                            "<b>ROCE:</b> "
                            "%{y:.2f}%"
                            "<extra></extra>"
                        ),
                    )
                )

            if len(fig.data) == 0:

                st.info(
                    "ROE and ROCE data is "
                    "not available."
                )

            else:

                fig.update_layout(

                    height=450,

                    hovermode="x unified",

                    xaxis=dict(
                        title="Financial Year",
                    ),

                    yaxis=dict(
                        title="Return (%)",
                        rangemode="tozero",
                    ),

                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1,
                    ),

                    margin=dict(
                        l=60,
                        r=40,
                        t=60,
                        b=60,
                    ),
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True,
                )

    st.markdown("---")