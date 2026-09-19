import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.etl.loader import read_excel

PROJECT_ROOT = Path(__file__).resolve().parents[2]


EXPECTED_ROWS = {
    "companies": 92,
    "profitandloss": 1276,
    "balancesheet": 1312,
    "cashflow": 1187,
    "analysis": 20,
    "documents": 1585,
    "prosandcons": 16,
    "sectors": 92,
    "stock_prices": 5520,
    "market_cap": 552,
    "financial_ratios": 1184,
    "peer_groups": 56,
}


@pytest.mark.parametrize(
    "table_name",
    [
        "companies",
        "profitandloss",
        "balancesheet",
        "cashflow",
        "analysis",
    ],
)
def test_core_file_row_counts(table_name):
    df = read_excel(
        PROJECT_ROOT,
        table_name,
    )

    assert len(df) == EXPECTED_ROWS[table_name]


@pytest.mark.parametrize(
    "table_name",
    [
        "documents",
        "prosandcons",
        "sectors",
        "stock_prices",
        "market_cap",
    ],
)
def test_supplementary_file_row_counts(table_name):
    df = read_excel(
        PROJECT_ROOT,
        table_name,
    )

    assert len(df) == EXPECTED_ROWS[table_name]


def test_financial_ratios_row_count():
    df = read_excel(
        PROJECT_ROOT,
        "financial_ratios",
    )

    assert len(df) == EXPECTED_ROWS["financial_ratios"]


def test_peer_groups_row_count():
    df = read_excel(
        PROJECT_ROOT,
        "peer_groups",
    )

    assert len(df) == EXPECTED_ROWS["peer_groups"]


def test_core_column_names():
    expected = {
        "companies": {
            "id",
            "company_name",
        },
        "profitandloss": {
            "company_id",
            "year",
            "sales",
            "net_profit",
        },
        "balancesheet": {
            "company_id",
            "year",
            "equity_capital",
            "borrowings",
        },
        "cashflow": {
            "company_id",
            "year",
            "operating_activity",
        },
        "analysis": {
            "company_id",
        },
    }

    for table_name, columns in expected.items():

        df = read_excel(
            PROJECT_ROOT,
            table_name,
        )

        assert columns.issubset(set(df.columns))


def test_remaining_column_names():
    expected = {
        "documents": {
            "company_id",
        },
        "prosandcons": {
            "company_id",
        },
        "sectors": {
            "company_id",
            "broad_sector",
        },
        "stock_prices": {
            "company_id",
            "date",
        },
        "market_cap": {
            "company_id",
        },
        "financial_ratios": {
            "company_id",
            "year",
        },
        "peer_groups": {
            "company_id",
        },
    }

    for table_name, columns in expected.items():

        df = read_excel(
            PROJECT_ROOT,
            table_name,
        )

        assert columns.issubset(set(df.columns))


def test_loader_normalizes_year_columns():
    for table_name in [
        "profitandloss",
        "balancesheet",
        "cashflow",
        "financial_ratios",
    ]:

        df = read_excel(
            PROJECT_ROOT,
            table_name,
        )

        assert "year" in df.columns

        valid_years = df["year"].dropna().astype(str)

        assert valid_years.str.match(r"^\d{4}-\d{2}$").all()


def test_loader_converts_numeric_columns():
    checks = {
        "companies": "roe_percentage",
        "profitandloss": "sales",
        "balancesheet": "borrowings",
        "cashflow": "operating_activity",
        "market_cap": "market_cap_crore",
        "financial_ratios": "return_on_equity_pct",
    }

    for table_name, column in checks.items():

        df = read_excel(
            PROJECT_ROOT,
            table_name,
        )

        assert column in df.columns

        assert pd.api.types.is_numeric_dtype(df[column])
