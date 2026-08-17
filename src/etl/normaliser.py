"""
NIFTY 100 Financial Intelligence Platform
Sprint 1 - Normalisation Functions
"""

import re
import pandas as pd


MONTHS = {
    "jan": "01",
    "feb": "02",
    "mar": "03",
    "apr": "04",
    "may": "05",
    "jun": "06",
    "jul": "07",
    "aug": "08",
    "sep": "09",
    "oct": "10",
    "nov": "11",
    "dec": "12",
}


def normalize_ticker(value):
    """
    Normalize company ticker.

    Example:
        ' tcs ' -> 'TCS'
        'Infy' -> 'INFY'
    """

    if pd.isna(value):
        return ""

    value = str(value)

    value = value.replace("\n", " ")
    value = value.strip()
    value = value.upper()

    # Remove unnecessary spaces
    value = re.sub(r"\s+", "", value)

    return value


def normalize_year(value):
    """
    Normalize financial year/date to YYYY-MM.

    Supported examples:
        Mar-23       -> 2023-03
        Mar 2013     -> 2013-03
        Dec 2012     -> 2012-12
        2023         -> 2023-03
        FY2023       -> 2023-03
        2023-04      -> 2023-04
        2023-03-31   -> 2023-03
    """

    if pd.isna(value):
        raise ValueError("Year is null")

    text = str(value).strip()

    if not text:
        raise ValueError("Year is empty")

    text = text.replace("–", "-")
    text = text.replace("—", "-")

    # YYYY-MM
    match = re.fullmatch(r"(\d{4})-(\d{1,2})", text)

    if match:
        year = int(match.group(1))
        month = int(match.group(2))

        if 1 <= month <= 12:
            return f"{year:04d}-{month:02d}"

    # YYYY-MM-DD
    match = re.match(
        r"^(\d{4})-(\d{1,2})-(\d{1,2})",
        text
    )

    if match:
        year = int(match.group(1))
        month = int(match.group(2))

        return f"{year:04d}-{month:02d}"

    # FY2023 / FY 2023
    match = re.fullmatch(
        r"FY\s*(\d{4})",
        text,
        re.IGNORECASE
    )

    if match:
        year = int(match.group(1))

        return f"{year:04d}-03"

    # Month + year
    match = re.search(
        r"\b([A-Za-z]{3,9})[ -]?(\d{2,4})\b",
        text
    )

    if match:

        month_text = match.group(1)
        year_text = match.group(2)

        month = MONTHS.get(
            month_text[:3].lower()
        )

        if month:

            year = int(year_text)

            if year < 100:
                year = 2000 + year

            return f"{year:04d}-{month}"

    # Bare year
    match = re.fullmatch(
        r"(\d{4})",
        text
    )

    if match:

        year = int(match.group(1))

        return f"{year:04d}-03"

    # Pandas fallback
    parsed_date = pd.to_datetime(
        text,
        errors="coerce"
    )

    if pd.notna(parsed_date):

        return parsed_date.strftime("%Y-%m")

    raise ValueError(
        f"Unparseable year: {value!r}"
    )