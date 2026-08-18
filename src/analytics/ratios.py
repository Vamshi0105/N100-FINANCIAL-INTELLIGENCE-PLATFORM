"""
Financial Ratio Engine
Day 08-09: Profitability, Leverage and Efficiency Ratios
"""


def safe_divide(numerator, denominator):
    """Safely divide two numbers."""
    if denominator is None:
        return None

    if denominator == 0:
        return None

    return numerator / denominator


def net_profit_margin(net_profit, sales):
    """
    Net Profit Margin =
        Net Profit / Sales * 100

    Returns None when sales = 0.
    """
    if sales is None or sales == 0:
        return None

    if net_profit is None:
        return None

    return (net_profit / sales) * 100


def operating_profit_margin(operating_profit, sales):
    """
    Operating Profit Margin =
        Operating Profit / Sales * 100
    """
    if sales is None or sales == 0:
        return None

    if operating_profit is None:
        return None

    return (operating_profit / sales) * 100


def cross_check_opm(computed_opm, source_opm, tolerance=1.0):
    """
    Compare computed OPM with source OPM.

    Returns:
        True  -> mismatch > tolerance
        False -> within tolerance
        None  -> cannot compare
    """

    if computed_opm is None or source_opm is None:
        return None

    return abs(computed_opm - source_opm) > tolerance


def return_on_equity(net_profit, equity_capital, reserves):
    """
    ROE =
        Net Profit /
        (Equity Capital + Reserves) * 100

    Returns None when equity + reserves <= 0.
    """

    if net_profit is None:
        return None

    if equity_capital is None:
        equity_capital = 0

    if reserves is None:
        reserves = 0

    equity = equity_capital + reserves

    if equity <= 0:
        return None

    return (net_profit / equity) * 100


def return_on_capital_employed(
    ebit,
    equity_capital,
    reserves,
    borrowings
):
    """
    ROCE =
        EBIT /
        (Equity + Reserves + Borrowings) * 100
    """

    if ebit is None:
        return None

    equity_capital = equity_capital or 0
    reserves = reserves or 0
    borrowings = borrowings or 0

    capital_employed = (
        equity_capital +
        reserves +
        borrowings
    )

    if capital_employed <= 0:
        return None

    return (ebit / capital_employed) * 100


def return_on_assets(net_profit, total_assets):
    """
    ROA =
        Net Profit / Total Assets * 100
    """

    if net_profit is None:
        return None

    if total_assets is None or total_assets == 0:
        return None

    return (net_profit / total_assets) * 100


# ============================================================
# DAY 09 - LEVERAGE & EFFICIENCY
# ============================================================

def debt_to_equity(borrowings, equity_capital, reserves):
    """
    Debt-to-Equity =
        Borrowings / (Equity Capital + Reserves)

    Debt-free company returns 0 instead of None.
    """

    borrowings = borrowings or 0
    equity_capital = equity_capital or 0
    reserves = reserves or 0

    equity = equity_capital + reserves

    if borrowings == 0:
        return 0

    if equity <= 0:
        return None

    return borrowings / equity


def high_leverage_flag(de_ratio, broad_sector):
    """
    D/E > 5 is considered high leverage,
    except for Financials.
    """

    if de_ratio is None:
        return False

    if broad_sector == "Financials":
        return False

    return de_ratio > 5


def interest_coverage_ratio(
    operating_profit,
    other_income,
    interest
):
    """
    ICR =
        (Operating Profit + Other Income) / Interest

    Returns None when interest = 0.
    """

    if interest is None or interest == 0:
        return None

    operating_profit = operating_profit or 0
    other_income = other_income or 0

    return (operating_profit + other_income) / interest


def interest_coverage_label(icr):
    """
    Debt-free label for ICR=None.
    """

    if icr is None:
        return "Debt Free"

    return None


def interest_coverage_warning(icr):
    """
    Warning when ICR < 1.5.
    """

    if icr is None:
        return False

    return icr < 1.5


def net_debt(borrowings, investments):
    """
    Net Debt =
        Borrowings - Investments
    """

    borrowings = borrowings or 0
    investments = investments or 0

    return borrowings - investments


def asset_turnover(sales, total_assets):
    """
    Asset Turnover =
        Sales / Total Assets
    """

    if total_assets is None or total_assets == 0:
        return None

    if sales is None:
        return None

    return sales / total_assets