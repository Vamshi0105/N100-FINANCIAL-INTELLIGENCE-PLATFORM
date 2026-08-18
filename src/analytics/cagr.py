"""
CAGR Engine

Handles:
1. Positive -> Positive
2. Positive -> Negative
3. Negative -> Positive
4. Negative -> Negative
5. Zero Base
6. Insufficient Data
"""


def calculate_cagr(start_value, end_value, years):
    """
    Calculate CAGR.

    Formula:
        ((end / start) ** (1 / n) - 1) * 100

    Returns:
        (value, flag)
    """

    if years is None or years <= 0:
        return None, "INSUFFICIENT"

    if start_value is None or end_value is None:
        return None, "INSUFFICIENT"

    # Zero base
    if start_value == 0:
        return None, "ZERO_BASE"

    # Positive -> Positive
    if start_value > 0 and end_value > 0:

        cagr = (
            ((end_value / start_value) ** (1 / years))
            - 1
        ) * 100

        return cagr, None

    # Positive -> Negative
    if start_value > 0 and end_value < 0:
        return None, "DECLINE_TO_LOSS"

    # Negative -> Positive
    if start_value < 0 and end_value > 0:
        return None, "TURNAROUND"

    # Negative -> Negative
    if start_value < 0 and end_value < 0:
        return None, "BOTH_NEGATIVE"

    return None, "INSUFFICIENT"


def get_cagr_from_series(values, years):
    """
    Calculate CAGR using a chronological series.

    Example:

    values = {
        2020: 100,
        2021: 110,
        2022: 120,
        2023: 130,
        2024: 150
    }

    years = 5

    Start and end values must have the required
    year distance.
    """

    if not values:
        return None, "INSUFFICIENT"

    sorted_years = sorted(values.keys())

    if len(sorted_years) < years:
        return None, "INSUFFICIENT"

    start_year = sorted_years[-years]
    end_year = sorted_years[-1]

    actual_year_difference = end_year - start_year

    if actual_year_difference < years - 1:
        return None, "INSUFFICIENT"

    return calculate_cagr(
        values[start_year],
        values[end_year],
        actual_year_difference
    )


def revenue_cagr(values, years):
    return get_cagr_from_series(values, years)


def pat_cagr(values, years):
    return get_cagr_from_series(values, years)


def eps_cagr(values, years):
    return get_cagr_from_series(values, years)