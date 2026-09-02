from src.screener.presets import (
    PRESETS,
    get_preset,
    list_presets,
)


def test_six_presets_exist():

    assert len(PRESETS) == 6


def test_quality_compounder_exists():

    preset = get_preset(
        "quality_compounder"
    )

    assert preset["return_on_equity_pct_min"] == 15


def test_value_pick_exists():

    preset = get_preset(
        "value_pick"
    )

    assert preset["pe_ratio_max"] == 20


def test_growth_accelerator_exists():

    preset = get_preset(
        "growth_accelerator"
    )

    assert preset["pat_cagr_5yr_min"] == 20


def test_dividend_champion_exists():

    preset = get_preset(
        "dividend_champion"
    )

    assert preset["dividend_yield_pct_min"] == 2


def test_debt_free_blue_chip_exists():

    preset = get_preset(
        "debt_free_blue_chip"
    )

    assert preset["return_on_equity_pct_min"] == 12


def test_turnaround_watch_exists():

    preset = get_preset(
        "turnaround_watch"
    )

    assert preset["revenue_cagr_3yr_min"] == 10


def test_list_presets():

    presets = list_presets()

    assert len(presets) == 6