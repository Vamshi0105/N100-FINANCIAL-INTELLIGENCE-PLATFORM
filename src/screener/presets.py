"""
Preset financial screeners.

Each preset defines a set of thresholds that can be passed
to the screener engine.
"""

PRESETS = {

    "quality_compounder": {
        "return_on_equity_pct_min": 15,
        "debt_to_equity_max": 1.0,
        "free_cash_flow_cr_min": 0,
        "revenue_cagr_5yr_min": 10,
    },

    "value_pick": {
        "pe_ratio_max": 20,
        "pb_ratio_max": 3.0,
        "debt_to_equity_max": 2.0,
        "dividend_yield_pct_min": 1,
    },

    "growth_accelerator": {
        "pat_cagr_5yr_min": 20,
        "revenue_cagr_5yr_min": 15,
        "debt_to_equity_max": 2.0,
    },

    "dividend_champion": {
        "dividend_yield_pct_min": 2,
        "dividend_payout_ratio_pct_max": 80,
        "free_cash_flow_cr_min": 0,
    },

    "debt_free_blue_chip": {
        "debt_to_equity_max": 0.000001,
        "return_on_equity_pct_min": 12,
        "sales_min": 5000,
    },

    "turnaround_watch": {
        "revenue_cagr_3yr_min": 10,
        "free_cash_flow_cr_min": 0,
        "debt_to_equity_declining": True,
    },
}


def get_preset(name: str) -> dict:
    """
    Return configuration for a named screener preset.
    """

    if name not in PRESETS:
        available = ", ".join(PRESETS.keys())
        raise ValueError(
            f"Unknown preset: {name}. "
            f"Available presets: {available}"
        )

    return PRESETS[name]


def list_presets() -> list:
    """
    Return all available preset names.
    """

    return list(PRESETS.keys())
def run_preset(preset_name, screener_function):
    """
    Load and run a preset through the screener engine.
    """

    config = get_preset(preset_name)

    return screener_function(config)