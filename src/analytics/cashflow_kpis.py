"""
Cash Flow KPIs
Day 11
"""


def free_cash_flow(operating_activity, investing_activity):
    """
    FCF =
        Operating Activity + Investing Activity

    Negative FCF is allowed.
    """

    operating_activity = operating_activity or 0
    investing_activity = investing_activity or 0

    return operating_activity + investing_activity


def cfo_pat_ratio(cfo, pat):
    """
    CFO / PAT
    """

    if pat is None or pat == 0:
        return None

    if cfo is None:
        return None

    return cfo / pat


def cfo_quality_score(cfo, pat):
    """
    CFO Quality:

    > 1.0      High Quality
    0.5 - 1.0  Moderate
    < 0.5      Accrual Risk
    """

    ratio = cfo_pat_ratio(cfo, pat)

    if ratio is None:
        return None, None

    if ratio > 1.0:
        return ratio, "High Quality"

    if ratio >= 0.5:
        return ratio, "Moderate"

    return ratio, "Accrual Risk"


def average_cfo_pat(cfo_pat_ratios):
    """
    Average CFO/PAT over available years.
    """

    valid = [
        value
        for value in cfo_pat_ratios
        if value is not None
    ]

    if not valid:
        return None

    return sum(valid) / len(valid)


def average_cfo_quality(cfo_pat_ratios):
    """
    Convert five-year average CFO/PAT
    into quality label.
    """

    average = average_cfo_pat(cfo_pat_ratios)

    if average is None:
        return None

    if average > 1.0:
        return "High Quality"

    if average >= 0.5:
        return "Moderate"

    return "Accrual Risk"


def capex_intensity(investing_activity, sales):
    """
    CapEx Intensity =
        abs(Investing Activity) / Sales * 100
    """

    if sales is None or sales == 0:
        return None

    investing_activity = investing_activity or 0

    return abs(investing_activity) / sales * 100


def capex_intensity_label(capex_pct):
    """
    <3%  = Asset Light
    3-8%  = Moderate
    >8%   = Capital Intensive
    """

    if capex_pct is None:
        return None

    if capex_pct < 3:
        return "Asset Light"

    if capex_pct <= 8:
        return "Moderate"

    return "Capital Intensive"


def fcf_conversion_rate(fcf, operating_profit):
    """
    FCF Conversion =
        FCF / Operating Profit * 100
    """

    if operating_profit is None or operating_profit == 0:
        return None

    if fcf is None:
        return None

    return (fcf / operating_profit) * 100


def sign(value):
    """
    Convert number into + / - / 0.
    """

    if value is None:
        return "0"

    if value > 0:
        return "+"

    if value < 0:
        return "-"

    return "0"


def capital_allocation_pattern(
    cfo,
    cfi,
    cff,
    cfo_pat=None
):
    """
    Capital allocation classifier.

    (+,-,-) = Reinvestor
    (+,-,-) with high CFO/PAT = Shareholder Returns
    (+,+,-) = Liquidating Assets
    (-,+,+) = Distress Signal
    (-,-,+) = Growth Funded by Debt
    (+,+,+) = Cash Accumulator
    (-,-,-) = Pre-Revenue
    (+,-,+) = Mixed
    """

    cfo_sign = sign(cfo)
    cfi_sign = sign(cfi)
    cff_sign = sign(cff)

    pattern = (
        cfo_sign,
        cfi_sign,
        cff_sign
    )

    # Special case
    if pattern == ("+", "-", "-"):

        if cfo_pat is not None and cfo_pat > 1.0:
            return "Shareholder Returns"

        return "Reinvestor"

    if pattern == ("+", "+", "-"):
        return "Liquidating Assets"

    if pattern == ("-", "+", "+"):
        return "Distress Signal"

    if pattern == ("-", "-", "+"):
        return "Growth Funded by Debt"

    if pattern == ("+", "+", "+"):
        return "Cash Accumulator"

    if pattern == ("-", "-", "-"):
        return "Pre-Revenue"

    if pattern == ("+", "-", "+"):
        return "Mixed"

    return "Unclassified"