from src.analytics.ratios import (
    asset_turnover,
    debt_to_equity,
    high_leverage_flag,
    interest_coverage_label,
    interest_coverage_ratio,
    interest_coverage_warning,
    net_debt,
)


def icr_label(icr):
    return interest_coverage_label(icr)


def icr_warning_flag(icr):
    return interest_coverage_warning(icr)
