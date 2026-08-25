def calculate_cagr(start, end, years, available_years=None):
    """
    Calculate CAGR and return (value, flag).

    Formula:
        ((end / start) ** (1 / years) - 1) * 100
    """

    if available_years is not None and available_years < years:
        return None, "INSUFFICIENT"

    if start == 0:
        return None, "ZERO_BASE"

    # Positive -> Positive
    if start > 0 and end > 0:
        cagr = ((end / start) ** (1 / years) - 1) * 100
        return cagr, None

    # Positive -> Negative
    if start > 0 and end < 0:
        return None, "DECLINE_TO_LOSS"

    # Negative -> Positive
    if start < 0 and end > 0:
        return None, "TURNAROUND"

    # Negative -> Negative
    if start < 0 and end < 0:
        return None, "BOTH_NEGATIVE"

    # End is zero
    if end == 0:
        if start > 0:
            return None, "DECLINE_TO_LOSS"

        if start < 0:
            return None, "BOTH_NEGATIVE"

    return None, None


def revenue_cagr(start, end, years, available_years=None):
    return calculate_cagr(start, end, years, available_years)


def pat_cagr(start, end, years, available_years=None):
    return calculate_cagr(start, end, years, available_years)


def eps_cagr(start, end, years, available_years=None):
    return calculate_cagr(start, end, years, available_years)


def calculate_growth_metrics(start, end, available_years):
    """
    Calculate 3-year, 5-year and 10-year CAGR metrics.

    Returns separate value and flag fields for each metric.
    """

    result = {}

    for years in (3, 5, 10):
        value, flag = calculate_cagr(
            start,
            end,
            years,
            available_years,
        )

        result[f"cagr_{years}yr"] = value
        result[f"cagr_{years}yr_flag"] = flag

    return result