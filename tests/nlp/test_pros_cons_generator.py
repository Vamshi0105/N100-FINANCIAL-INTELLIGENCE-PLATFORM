
"""
Tests for Day 30 — NLP Auto Pros/Cons Generator.
"""

from __future__ import annotations

import pandas as pd

from src.nlp.pros_cons_generator import (
    MIN_CONFIDENCE,
    build_record,
    confidence_from_margin,
    confidence_from_series,
    generate_fallback_con,
    generate_fallback_pro,
    has_consecutive_positive,
    is_financial_company,
    latest_n_values,
    normalize_company_id,
    normalize_year,
    strictly_decreasing,
    strictly_increasing,
    sustained_above,
    to_numeric,
    verify_company_coverage,
)


# ---------------------------------------------------------
# Normalization helper tests
# ---------------------------------------------------------


def test_normalize_company_id_uppercases_and_strips():
    assert normalize_company_id("  abb ") == "ABB"


def test_normalize_company_id_none_returns_none():
    assert normalize_company_id(None) is None


def test_normalize_company_id_empty_returns_none():
    assert normalize_company_id("   ") is None


def test_normalize_year_integer():
    assert normalize_year(2024) == 2024


def test_normalize_year_date_string():
    assert normalize_year("2024-03-31") == 2024


def test_normalize_year_year_month():
    assert normalize_year("2023-03") == 2023


def test_normalize_year_invalid_returns_none():
    assert normalize_year("invalid") is None


def test_to_numeric_valid_number():
    assert to_numeric("123.45") == 123.45


def test_to_numeric_none_returns_none():
    assert to_numeric(None) is None


def test_to_numeric_invalid_returns_none():
    assert to_numeric("abc") is None


# ---------------------------------------------------------
# Historical helper tests
# ---------------------------------------------------------


def test_latest_n_values_returns_latest_values():
    df = pd.DataFrame(
        {
            "year_numeric": [2021, 2022, 2023, 2024],
            "value": [10, 20, 30, 40],
        }
    )

    result = latest_n_values(
        df,
        "value",
        3,
    )

    assert result == [20.0, 30.0, 40.0]


def test_latest_n_values_ignores_missing_values():
    df = pd.DataFrame(
        {
            "year_numeric": [2021, 2022, 2023, 2024],
            "value": [10, None, 30, 40],
        }
    )

    result = latest_n_values(
        df,
        "value",
        3,
    )

    assert result == [10.0, 30.0, 40.0]


def test_has_consecutive_positive_true():
    assert has_consecutive_positive(
        [10.0, 20.0, 30.0],
        3,
    )


def test_has_consecutive_positive_false_when_negative():
    assert not has_consecutive_positive(
        [10.0, -5.0, 30.0],
        3,
    )


def test_has_consecutive_positive_false_when_insufficient_values():
    assert not has_consecutive_positive(
        [10.0, 20.0],
        3,
    )


def test_strictly_increasing_true():
    assert strictly_increasing(
        [10.0, 20.0, 30.0]
    )


def test_strictly_increasing_false():
    assert not strictly_increasing(
        [10.0, 20.0, 15.0]
    )


def test_strictly_increasing_equal_values_false():
    assert not strictly_increasing(
        [10.0, 10.0, 20.0]
    )


def test_strictly_decreasing_true():
    assert strictly_decreasing(
        [30.0, 20.0, 10.0]
    )


def test_strictly_decreasing_false():
    assert not strictly_decreasing(
        [30.0, 20.0, 25.0]
    )


def test_sustained_above_true():
    assert sustained_above(
        [25.0, 30.0, 35.0],
        20.0,
        3,
    )


def test_sustained_above_false():
    assert not sustained_above(
        [25.0, 15.0, 35.0],
        20.0,
        3,
    )


# ---------------------------------------------------------
# Financial company tests
# ---------------------------------------------------------


def test_is_financial_company_bank():
    sector_row = pd.Series(
        {
            "broad_sector": "Financial Services",
            "sub_sector": "Private Bank",
        }
    )

    assert is_financial_company(
        sector_row
    )


def test_is_financial_company_insurance():
    sector_row = pd.Series(
        {
            "broad_sector": "Insurance",
            "sub_sector": "Life Insurance",
        }
    )

    assert is_financial_company(
        sector_row
    )


def test_is_financial_company_false_for_it():
    sector_row = pd.Series(
        {
            "broad_sector": "Information Technology",
            "sub_sector": "Software",
        }
    )

    assert not is_financial_company(
        sector_row
    )


def test_is_financial_company_none_returns_false():
    assert not is_financial_company(
        None
    )


# ---------------------------------------------------------
# Confidence scoring tests
# ---------------------------------------------------------


def test_confidence_from_margin_above_threshold():
    result = confidence_from_margin(
        actual=30.0,
        threshold=20.0,
        scale=20.0,
    )

    assert result > 65.0
    assert result <= 100.0


def test_confidence_from_margin_below_direction():
    result = confidence_from_margin(
        actual=5.0,
        threshold=10.0,
        scale=10.0,
        direction="below",
    )

    assert result > 65.0
    assert result <= 100.0


def test_confidence_from_margin_minimum_confidence():
    result = confidence_from_margin(
        actual=20.0,
        threshold=20.0,
        scale=10.0,
    )

    assert result >= 61.0


def test_confidence_from_series():
    result = confidence_from_series(
        [10.0, 20.0, 30.0],
        3,
    )

    assert result == 95.0


# ---------------------------------------------------------
# Record construction tests
# ---------------------------------------------------------


def test_build_record_above_minimum_confidence():
    record = build_record(
        company_id="ABB",
        signal_type="pro",
        rule_id="PRO_01",
        text="Strong return on equity",
        confidence=80.0,
    )

    assert record is not None
    assert record["company_id"] == "ABB"
    assert record["type"] == "pro"
    assert record["rule_id"] == "PRO_01"
    assert record["confidence_pct"] == 80.0


def test_build_record_at_minimum_confidence_excluded():
    record = build_record(
        company_id="ABB",
        signal_type="pro",
        rule_id="PRO_TEST",
        text="Test signal",
        confidence=MIN_CONFIDENCE,
    )

    assert record is None


def test_build_record_below_minimum_confidence_excluded():
    record = build_record(
        company_id="ABB",
        signal_type="con",
        rule_id="CON_TEST",
        text="Test signal",
        confidence=50.0,
    )

    assert record is None


# ---------------------------------------------------------
# Fallback signal tests
# ---------------------------------------------------------


def test_generate_fallback_pro_positive_roe():
    ratios = pd.DataFrame(
        {
            "year_numeric": [2024],
            "return_on_equity_pct": [15.0],
        }
    )

    record = generate_fallback_pro(
        "ABB",
        ratios,
    )

    assert record["company_id"] == "ABB"
    assert record["type"] == "pro"
    assert record["rule_id"] == "PRO_FALLBACK"
    assert record["confidence_pct"] > MIN_CONFIDENCE


def test_generate_fallback_pro_without_roe():
    ratios = pd.DataFrame(
        {
            "year_numeric": [2024],
            "return_on_equity_pct": [None],
        }
    )

    record = generate_fallback_pro(
        "TEST",
        ratios,
    )

    assert record["type"] == "pro"
    assert record["rule_id"] == "PRO_FALLBACK"
    assert record["confidence_pct"] == 61.0


def test_generate_fallback_con_moderate_growth():
    ratios = pd.DataFrame(
        {
            "year_numeric": [2024],
            "revenue_cagr_5yr": [8.0],
        }
    )

    record = generate_fallback_con(
        "ABB",
        ratios,
    )

    assert record["company_id"] == "ABB"
    assert record["type"] == "con"
    assert record["rule_id"] == "CON_FALLBACK"
    assert record["confidence_pct"] == 65.0


def test_generate_fallback_con_strong_growth():
    ratios = pd.DataFrame(
        {
            "year_numeric": [2024],
            "revenue_cagr_5yr": [20.0],
        }
    )

    record = generate_fallback_con(
        "ABB",
        ratios,
    )

    assert record["type"] == "con"
    assert record["rule_id"] == "CON_FALLBACK"
    assert record["confidence_pct"] == 61.0


# ---------------------------------------------------------
# Coverage verification tests
# ---------------------------------------------------------


def test_verify_company_coverage_passes():
    companies_df = pd.DataFrame(
        {
            "company_id": [
                "ABB",
                "TCS",
            ]
        }
    )

    output_df = pd.DataFrame(
        {
            "company_id": [
                "ABB",
                "ABB",
                "TCS",
                "TCS",
            ],
            "type": [
                "pro",
                "con",
                "pro",
                "con",
            ],
        }
    )

    verify_company_coverage(
        output_df,
        companies_df,
    )


def test_verify_company_coverage_fails_missing_pro():
    companies_df = pd.DataFrame(
        {
            "company_id": [
                "ABB",
            ]
        }
    )

    output_df = pd.DataFrame(
        {
            "company_id": [
                "ABB",
            ],
            "type": [
                "con",
            ],
        }
    )

    try:

        verify_company_coverage(
            output_df,
            companies_df,
        )

        assert False, (
            "Expected ValueError"
        )

    except ValueError as error:

        assert (
            "missing Pro signals"
            in str(error)
        )


def test_verify_company_coverage_fails_missing_con():
    companies_df = pd.DataFrame(
        {
            "company_id": [
                "ABB",
            ]
        }
    )

    output_df = pd.DataFrame(
        {
            "company_id": [
                "ABB",
            ],
            "type": [
                "pro",
            ],
        }
    )

    try:

        verify_company_coverage(
            output_df,
            companies_df,
        )

        assert False, (
            "Expected ValueError"
        )

    except ValueError as error:

        assert (
            "missing Con signals"
            in str(error)
        )

