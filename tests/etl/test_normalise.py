import sys
from pathlib import Path

import pytest

sys.path.insert(
    0,
    str(
        Path(__file__)
        .resolve()
        .parents[2]
    )
)

from src.etl.normaliser import (
    normalize_year,
    normalize_ticker
)


@pytest.mark.parametrize(
    "raw,expected",
    [

        ("Mar-23", "2023-03"),
        ("Mar 23", "2023-03"),
        ("Mar 2013", "2013-03"),
        ("Dec 2012", "2012-12"),

        ("2013", "2013-03"),
        ("2024", "2024-03"),

        ("FY2023", "2023-03"),
        ("FY 2022", "2022-03"),

        ("2023-04", "2023-04"),
        ("2023-12", "2023-12"),

        ("2023-03-31", "2023-03"),
        ("2024-01-15", "2024-01"),

        ("Jan 2020", "2020-01"),
        ("Feb-19", "2019-02"),
        ("Jun 2021", "2021-06"),
        ("Sep 2022", "2022-09"),
        ("Oct-20", "2020-10"),
        ("Nov 2018", "2018-11"),
        ("Apr-17", "2017-04"),
        ("May 2016", "2016-05")
    ]
)
def test_normalize_year(
    raw,
    expected
):

    assert (
        normalize_year(raw)
        == expected
    )


@pytest.mark.parametrize(
    "raw,expected",
    [

        (" tcs ", "TCS"),
        ("Tcs", "TCS"),
        ("INFY\n", "INFY"),
        ("hdfcbank", "HDFCBANK"),
        (" ADANIENT ", "ADANIENT"),
        ("itc", "ITC"),
        ("SBIN", "SBIN"),
        ("reliance", "RELIANCE"),
        ("  LT  ", "LT"),
        ("M&M", "M&M"),
        ("BAJAJ-AUTO", "BAJAJ-AUTO"),
        ("  AXISBANK\n", "AXISBANK"),
        ("icicibank", "ICICIBANK"),
        ("TATASTEEL ", "TATASTEEL"),
        ("  nse:infy ", "NSE:INFY")
    ]
)
def test_normalize_ticker(
    raw,
    expected
):

    assert (
        normalize_ticker(raw)
        == expected
    )