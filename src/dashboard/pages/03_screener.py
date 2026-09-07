import pandas as pd
import streamlit as st

from src.screener.engine import run_screener
from src.screener.presets import get_preset


# --------------------------------------------------
# Page configuration
# --------------------------------------------------

PRESET_BUTTONS = {
    "Quality": "quality_compounder",
    "Value": "value_pick",
    "Growth": "growth_accelerator",
    "Dividend": "dividend_champion",
    "Debt-Free": "debt_free_blue_chip",
    "Turnaround": "turnaround_watch",
}


SLIDER_DEFAULTS = {
    "return_on_equity_pct_min": 0.0,
    "debt_to_equity_max": 10.0,
    "free_cash_flow_cr_min": -100000.0,
    "revenue_cagr_3yr_min": -100.0,
    "pat_cagr_5yr_min": -100.0,
    "opm_min": -100.0,
    "pe_ratio_max": 200.0,
    "pb_ratio_max": 50.0,
    "dividend_yield_pct_min": 0.0,
    "icr_min": -100.0,
}


def initialise_session_state():
    """Initialise screener slider values."""

    for key, value in SLIDER_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value

    if "preset_filters" not in st.session_state:
        st.session_state.preset_filters = {}

    if "active_preset" not in st.session_state:
        st.session_state.active_preset = None


def reset_filters():
    """Reset all slider filters."""

    for key, value in SLIDER_DEFAULTS.items():
        st.session_state[key] = value

    st.session_state.preset_filters = {}
    st.session_state.active_preset = None


def apply_preset(preset_name: str):
    """
    Apply a screener preset.

    Values represented by visible sliders update the sidebar.
    Extra preset filters are retained separately.
    """

    preset = get_preset(preset_name)

    slider_filters = {
        key: value
        for key, value in preset.items()
        if key in SLIDER_DEFAULTS
    }

    extra_filters = {
        key: value
        for key, value in preset.items()
        if key not in SLIDER_DEFAULTS
    }

    # Map existing 5-year revenue CAGR presets to the
    # Day 24 Revenue CAGR slider.
    if "revenue_cagr_5yr_min" in extra_filters:
        st.session_state.revenue_cagr_3yr_min = (
            extra_filters["revenue_cagr_5yr_min"]
        )
        del extra_filters["revenue_cagr_5yr_min"]

    # Reset first so each preset starts clean.
    for key, value in SLIDER_DEFAULTS.items():
        st.session_state[key] = value

    # Apply visible preset values.
    for key, value in slider_filters.items():
        st.session_state[key] = value

    st.session_state.preset_filters = extra_filters
    st.session_state.active_preset = preset_name


def build_filters():
    """
    Build screener filter dictionary from sidebar values.

    Default 'wide' values are converted to None so they
    do not unintentionally filter companies.
    """

    filters = {}

    # ROE
    if (
        st.session_state.return_on_equity_pct_min
        != SLIDER_DEFAULTS["return_on_equity_pct_min"]
    ):
        filters["return_on_equity_pct_min"] = (
            st.session_state.return_on_equity_pct_min
        )

    # Debt-to-Equity
    if (
        st.session_state.debt_to_equity_max
        != SLIDER_DEFAULTS["debt_to_equity_max"]
    ):
        filters["debt_to_equity_max"] = (
            st.session_state.debt_to_equity_max
        )

    # Free Cash Flow
    if (
        st.session_state.free_cash_flow_cr_min
        != SLIDER_DEFAULTS["free_cash_flow_cr_min"]
    ):
        filters["free_cash_flow_cr_min"] = (
            st.session_state.free_cash_flow_cr_min
        )

    # Revenue CAGR
    if (
        st.session_state.revenue_cagr_3yr_min
        != SLIDER_DEFAULTS["revenue_cagr_3yr_min"]
    ):
        filters["revenue_cagr_3yr_min"] = (
            st.session_state.revenue_cagr_3yr_min
        )

    # PAT CAGR
    if (
        st.session_state.pat_cagr_5yr_min
        != SLIDER_DEFAULTS["pat_cagr_5yr_min"]
    ):
        filters["pat_cagr_5yr_min"] = (
            st.session_state.pat_cagr_5yr_min
        )

    # OPM
    if st.session_state.opm_min != SLIDER_DEFAULTS["opm_min"]:
        filters["opm_min"] = st.session_state.opm_min

    # P/E
    if (
        st.session_state.pe_ratio_max
        != SLIDER_DEFAULTS["pe_ratio_max"]
    ):
        filters["pe_ratio_max"] = (
            st.session_state.pe_ratio_max
        )

    # P/B
    if (
        st.session_state.pb_ratio_max
        != SLIDER_DEFAULTS["pb_ratio_max"]
    ):
        filters["pb_ratio_max"] = (
            st.session_state.pb_ratio_max
        )

    # Dividend Yield
    if (
        st.session_state.dividend_yield_pct_min
        != SLIDER_DEFAULTS["dividend_yield_pct_min"]
    ):
        filters["dividend_yield_pct_min"] = (
            st.session_state.dividend_yield_pct_min
        )

    # Interest Coverage Ratio
    if st.session_state.icr_min != SLIDER_DEFAULTS["icr_min"]:
        filters["icr_min"] = st.session_state.icr_min

    # Preserve extra filters supplied by presets.
    filters.update(st.session_state.preset_filters)

    return filters


def get_display_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
    """
    Return the required Day 24 visible screener columns.
    """

    display_columns = [
        "company_id",
        "name",
        "broad_sector",
        "composite_quality_score",
        "return_on_equity_pct",
        "debt_to_equity",
        "free_cash_flow_cr",
        "revenue_cagr_3yr",
        "pat_cagr_5yr",
        "operating_profit_margin_pct",
        "pe_ratio",
        "pb_ratio",
        "dividend_yield_pct",
        "interest_coverage",
    ]

    available_columns = [
        column
        for column in display_columns
        if column in dataframe.columns
    ]

    result = dataframe[available_columns].copy()

    # User-friendly column names.
    result = result.rename(
        columns={
            "company_id": "Company ID",
            "name": "Name",
            "broad_sector": "Sector",
            "composite_quality_score": "Composite Score",
            "return_on_equity_pct": "ROE %",
            "debt_to_equity": "Debt / Equity",
            "free_cash_flow_cr": "FCF (Cr)",
            "revenue_cagr_3yr": "Revenue CAGR 3Y %",
            "pat_cagr_5yr": "PAT CAGR 5Y %",
            "operating_profit_margin_pct": "OPM %",
            "pe_ratio": "P/E",
            "pb_ratio": "P/B",
            "dividend_yield_pct": "Dividend Yield %",
            "interest_coverage": "ICR",
        }
    )

    return result


def render():

    initialise_session_state()

    st.title("Financial Screener")

    st.caption(
        "Filter NIFTY 100 companies using financial "
        "quality, valuation, growth, dividend and leverage metrics."
    )

    # --------------------------------------------------
    # Preset buttons
    # --------------------------------------------------

    st.subheader("Quick Presets")

    preset_columns = st.columns(6)

    for column, (label, preset_name) in zip(
        preset_columns,
        PRESET_BUTTONS.items(),
    ):
        with column:
            if st.button(
                label,
                use_container_width=True,
                key=f"preset_{preset_name}",
            ):
                apply_preset(preset_name)
                st.rerun()

    if st.session_state.active_preset:
        pretty_name = (
            st.session_state.active_preset
            .replace("_", " ")
            .title()
        )

        st.success(
            f"Active preset: {pretty_name}"
        )

    # --------------------------------------------------
    # Sidebar filters
    # --------------------------------------------------

    st.sidebar.header("Screener Filters")

    if st.sidebar.button(
        "Reset Filters",
        use_container_width=True,
    ):
        reset_filters()
        st.rerun()

    st.sidebar.markdown("---")

    st.sidebar.slider(
        "ROE Minimum (%)",
        min_value=-50.0,
        max_value=100.0,
        step=1.0,
        key="return_on_equity_pct_min",
    )

    st.sidebar.slider(
        "Debt-to-Equity Maximum",
        min_value=0.0,
        max_value=10.0,
        step=0.1,
        key="debt_to_equity_max",
    )

    st.sidebar.slider(
        "Free Cash Flow Minimum (Cr)",
        min_value=-100000.0,
        max_value=100000.0,
        step=100.0,
        key="free_cash_flow_cr_min",
    )

    st.sidebar.slider(
        "Revenue CAGR Minimum (%)",
        min_value=-100.0,
        max_value=100.0,
        step=1.0,
        key="revenue_cagr_3yr_min",
    )

    st.sidebar.slider(
        "PAT CAGR Minimum (%)",
        min_value=-100.0,
        max_value=100.0,
        step=1.0,
        key="pat_cagr_5yr_min",
    )

    st.sidebar.slider(
        "OPM Minimum (%)",
        min_value=-100.0,
        max_value=100.0,
        step=1.0,
        key="opm_min",
    )

    st.sidebar.slider(
        "P/E Maximum",
        min_value=0.0,
        max_value=200.0,
        step=1.0,
        key="pe_ratio_max",
    )

    st.sidebar.slider(
        "P/B Maximum",
        min_value=0.0,
        max_value=50.0,
        step=0.1,
        key="pb_ratio_max",
    )

    st.sidebar.slider(
        "Dividend Yield Minimum (%)",
        min_value=0.0,
        max_value=20.0,
        step=0.1,
        key="dividend_yield_pct_min",
    )

    st.sidebar.slider(
        "ICR Minimum",
        min_value=-100.0,
        max_value=100.0,
        step=1.0,
        key="icr_min",
    )

    # --------------------------------------------------
    # Run screener
    # --------------------------------------------------

    filters = build_filters()

    try:

        results = run_screener(filters=filters)

    except Exception as error:

        st.error(
            f"Unable to run financial screener: {error}"
        )
        return

    display_dataframe = get_display_dataframe(results)

    # --------------------------------------------------
    # Result count
    # --------------------------------------------------

    result_count = len(display_dataframe)

    if result_count == 1:
        st.subheader("1 company matches your filters")
    else:
        st.subheader(
            f"{result_count} companies match your filters"
        )

    # --------------------------------------------------
    # Results table
    # --------------------------------------------------

    if display_dataframe.empty:

        st.warning(
            "No companies match the selected filters. "
            "Try widening one or more filters."
        )
        return

    st.dataframe(
        display_dataframe,
        use_container_width=True,
        hide_index=True,
    )

    # --------------------------------------------------
    # CSV download
    # --------------------------------------------------

    csv_data = display_dataframe.to_csv(
        index=False
    ).encode("utf-8")

    st.download_button(
        label="Download Results as CSV",
        data=csv_data,
        file_name="nifty100_screener_results.csv",
        mime="text/csv",
        use_container_width=True,
    )