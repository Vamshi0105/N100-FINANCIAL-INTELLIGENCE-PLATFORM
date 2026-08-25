import csv
from pathlib import Path


def free_cash_flow(operating_activity, investing_activity):
    """
    Free Cash Flow = Operating Activity + Investing Activity

    Negative FCF is allowed.
    """
    return operating_activity + investing_activity


def cfo_quality_score(cfo_values, pat_values):
    """
    Calculate average CFO / PAT ratio over 5 years.

    > 1.0     = High Quality
    0.5-1.0   = Moderate
    < 0.5     = Accrual Risk

    Returns:
        (score, label)

    Returns (None, None) if PAT is zero
    or no data is available.
    """

    if len(cfo_values) == 0 or len(pat_values) == 0:
        return None, None

    ratios = []

    for cfo, pat in zip(cfo_values, pat_values):
        if pat == 0:
            return None, None

        ratios.append(cfo / pat)

    score = sum(ratios) / len(ratios)

    if score > 1.0:
        label = "High Quality"
    elif score >= 0.5:
        label = "Moderate"
    else:
        label = "Accrual Risk"

    return score, label


def capex_intensity(investing_activity, sales):
    """
    CapEx Intensity = abs(Investing Activity) / Sales * 100

    < 3%   = Asset Light
    3-8%   = Moderate
    > 8%   = Capital Intensive
    """

    if sales == 0:
        return None, None

    intensity = abs(investing_activity) / sales * 100

    if intensity < 3:
        label = "Asset Light"
    elif intensity <= 8:
        label = "Moderate"
    else:
        label = "Capital Intensive"

    return intensity, label


def fcf_conversion_rate(fcf, operating_profit):
    """
    FCF Conversion Rate = FCF / Operating Profit * 100
    """

    if operating_profit == 0:
        return None

    return (fcf / operating_profit) * 100


def capital_allocation_pattern(
    cfo,
    cfi,
    cff,
    cfo_pat_ratio=None,
):
    """
    Classify capital allocation using signs of CFO, CFI and CFF.

    (+,-,-) = Reinvestor
    (+,-,-) with high CFO/PAT = Shareholder Returns
    (+,+,-) = Liquidating Assets
    (-,+,+) = Distress Signal
    (-,-,+) = Growth Funded by Debt
    (+,+,+) = Cash Accumulator
    (-,-,-) = Pre-Revenue
    (+,-,+) = Mixed
    """

    cfo_sign = "+" if cfo > 0 else "-" if cfo < 0 else "0"
    cfi_sign = "+" if cfi > 0 else "-" if cfi < 0 else "0"
    cff_sign = "+" if cff > 0 else "-" if cff < 0 else "0"

    signs = (cfo_sign, cfi_sign, cff_sign)

    # (+,-,-)
    if signs == ("+", "-", "-"):
        if cfo_pat_ratio is not None and cfo_pat_ratio > 1.0:
            return "Shareholder Returns"

        return "Reinvestor"

    # Remaining patterns
    patterns = {
        ("+", "+", "-"): "Liquidating Assets",
        ("-", "+", "+"): "Distress Signal",
        ("-", "-", "+"): "Growth Funded by Debt",
        ("+", "+", "+"): "Cash Accumulator",
        ("-", "-", "-"): "Pre-Revenue",
        ("+", "-", "+"): "Mixed",
    }

    return patterns.get(
        signs,
        f"CFO{cfo_sign} / CFI{cfi_sign} / CFF{cff_sign}",
    )


def generate_capital_allocation_csv(
    records,
    output_path="output/capital_allocation.csv",
):
    """
    Generate capital_allocation.csv.

    Required columns:
        company_id
        year
        cfo_sign
        cfi_sign
        cff_sign
        pattern_label

    Each record should contain:
        company_id
        year
        cfo
        cfi
        cff

    Optional:
        cfo_pat_ratio
    """

    output_file = Path(output_path)

    # Create output directory if it doesn't exist
    output_file.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "company_id",
        "year",
        "cfo_sign",
        "cfi_sign",
        "cff_sign",
        "pattern_label",
    ]

    with output_file.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for record in records:

            cfo = record["cfo"]
            cfi = record["cfi"]
            cff = record["cff"]

            cfo_sign = (
                "+"
                if cfo > 0
                else "-"
                if cfo < 0
                else "0"
            )

            cfi_sign = (
                "+"
                if cfi > 0
                else "-"
                if cfi < 0
                else "0"
            )

            cff_sign = (
                "+"
                if cff > 0
                else "-"
                if cff < 0
                else "0"
            )

            pattern_label = capital_allocation_pattern(
                cfo,
                cfi,
                cff,
                record.get("cfo_pat_ratio"),
            )

            writer.writerow(
                {
                    "company_id": record["company_id"],
                    "year": record["year"],
                    "cfo_sign": cfo_sign,
                    "cfi_sign": cfi_sign,
                    "cff_sign": cff_sign,
                    "pattern_label": pattern_label,
                }
            )