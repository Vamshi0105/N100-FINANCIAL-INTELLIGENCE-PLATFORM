import sqlite3
import logging
from pathlib import Path

import pandas as pd
import yaml

logger = logging.getLogger(__name__)

DATABASE_PATH = Path("data/nifty100.db")
CONFIG_PATH = Path("config/screener_config.yaml")


def load_screener_config(config_path=CONFIG_PATH):
    """Load screener configuration from YAML."""
    with open(config_path, "r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def load_financial_ratios(database_path=DATABASE_PATH):
    """
    Load financial ratios together with P&L, market cap,
    and sector information required by the screener.
    """
    connection = sqlite3.connect(database_path)

    query = """
    SELECT
        r.*,

        p.sales,
        p.net_profit,

        m.market_cap_crore,
        m.pe_ratio,
        m.pb_ratio,
        m.dividend_yield_pct,

        s.broad_sector,
        s.sub_sector

    FROM financial_ratios r

    LEFT JOIN profitandloss p
        ON r.company_id = p.company_id
        AND r.year = p.year

    LEFT JOIN market_cap m
        ON r.company_id = m.company_id
        AND r.year = m.year

    LEFT JOIN sectors s
        ON r.company_id = s.company_id
    """

    dataframe = pd.read_sql_query(query, connection)
    connection.close()

    logger.info("Loaded %s rows for screener", len(dataframe))
    return dataframe


def apply_filters(dataframe, filters):
    """
    Apply all configured screener threshold filters.

    Filters with a null value are skipped.
    """
    if filters is None:
        filters = {}

    result = dataframe.copy()

    # 1. ROE minimum
    if filters.get("roe_min") is not None:
        result = result[result["return_on_equity_pct"] >= filters["roe_min"]]

    # 2. Debt-to-Equity maximum
    # Financial companies automatically skip this filter.
    if filters.get("debt_to_equity_max") is not None:
        financials_mask = (
            result["broad_sector"].astype(str).str.lower().str.contains("financial")
        )

        non_financials = result[~financials_mask]
        financials = result[financials_mask]

        non_financials = non_financials[
            non_financials["debt_to_equity"] <= filters["debt_to_equity_max"]
        ]

        result = pd.concat([non_financials, financials], ignore_index=True)

    # 3. Free Cash Flow minimum
    if filters.get("free_cash_flow_min") is not None:
        result = result[result["free_cash_flow_cr"] >= filters["free_cash_flow_min"]]

    # 4. Revenue CAGR 5Y minimum
    if filters.get("revenue_cagr_5yr_min") is not None:
        result = result[result["revenue_cagr_5yr"] >= filters["revenue_cagr_5yr_min"]]

    # 5. PAT CAGR 5Y minimum
    if filters.get("pat_cagr_5yr_min") is not None:
        result = result[result["pat_cagr_5yr"] >= filters["pat_cagr_5yr_min"]]

    # 6. OPM minimum
    if filters.get("opm_min") is not None:
        result = result[result["operating_profit_margin_pct"] >= filters["opm_min"]]

    # 7. P/E maximum
    if filters.get("pe_max") is not None:
        result = result[result["pe_ratio"] <= filters["pe_max"]]

    # 8. P/B maximum
    if filters.get("pb_max") is not None:
        result = result[result["pb_ratio"] <= filters["pb_max"]]

    # 9. Dividend Yield minimum
    if filters.get("dividend_yield_min") is not None:
        result = result[result["dividend_yield_pct"] >= filters["dividend_yield_min"]]

    # 10. Interest Coverage Ratio minimum
    # Debt Free companies always pass.
    if filters.get("icr_min") is not None:
        numeric_pass = result["interest_coverage"] >= filters["icr_min"]
        debt_free_pass = result["icr_label"].astype(str).str.lower() == "debt free"
        result = result[numeric_pass | debt_free_pass]

    # 11. Market Cap minimum
    if filters.get("market_cap_min") is not None:
        result = result[result["market_cap_crore"] >= filters["market_cap_min"]]

    # 12. Net Profit minimum
    if filters.get("net_profit_min") is not None:
        result = result[result["net_profit"] >= filters["net_profit_min"]]

    # 13. EPS CAGR minimum
    # Uses 5-year EPS CAGR.
    if filters.get("eps_cagr_min") is not None:
        result = result[result["eps_cagr_5yr"] >= filters["eps_cagr_min"]]

    # 14. Asset Turnover minimum
    if filters.get("asset_turnover_min") is not None:
        result = result[result["asset_turnover"] >= filters["asset_turnover_min"]]

    # 15. Sales minimum
    if filters.get("sales_min") is not None:
        result = result[result["sales"] >= filters["sales_min"]]

    logger.info("Rows remaining after filters: %s", len(result))
    return result


def sort_results(dataframe, sorting):
    """Sort screener results."""
    if sorting is None:
        sorting = {}

    column = sorting.get("column", "composite_quality_score")
    ascending = sorting.get("ascending", False)

    if column not in dataframe.columns:
        logger.warning("Sort column not found: %s", column)
        return dataframe

    return dataframe.sort_values(by=column, ascending=ascending, na_position="last")


def run_screener(database_path=DATABASE_PATH, config_path=CONFIG_PATH):
    """Run the complete financial screener."""
    logger.info("Starting financial screener")

    config = load_screener_config(config_path)
    dataframe = load_financial_ratios(database_path)

    filters = config.get("filters", {})
    sorting = config.get("sorting", {})

    filtered_dataframe = apply_filters(dataframe, filters)
    sorted_dataframe = sort_results(filtered_dataframe, sorting)

    logger.info("Screener completed successfully")
    logger.info("Final result count: %s", len(sorted_dataframe))
    return sorted_dataframe


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s:%(name)s:%(message)s",
    )

    results = run_screener()

    print("\nScreener result count:", len(results))

    display_columns = [
        "company_id",
        "year",
        "broad_sector",
        "return_on_equity_pct",
        "debt_to_equity",
        "free_cash_flow_cr",
        "composite_quality_score",
    ]

    available_columns = [
        column for column in display_columns if column in results.columns
    ]

    print("\nSample results:")
    print(results[available_columns].head(20).to_string(index=False))

