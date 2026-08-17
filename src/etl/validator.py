"""
NIFTY 100 Financial Intelligence Platform
Sprint 1 - Data Quality Validation

DQ-01 to DQ-16
"""

import re
import pandas as pd
import numpy as np

from .normaliser import (
    normalize_ticker,
    normalize_year
)


BANK_TERMS = {
    "Financials",
    "Financial Services",
    "Banks",
    "Banking",
    "Finance"
}


def create_issue(
    rule,
    severity,
    table,
    company_id=None,
    year=None,
    field=None,
    message="",
    raw_value=None
):

    return {
        "rule_id": rule,
        "severity": severity,
        "table": table,
        "company_id": company_id,
        "year": year,
        "field": field,
        "issue": message,
        "raw_value": raw_value
    }


def validate_all(frames):

    issues = []

    companies = frames["companies"].copy()

    company_ids = (
        companies["id"]
        .map(normalize_ticker)
    )

    # ---------------------------------------------------------
    # DQ-01 Company Primary Key Uniqueness
    # ---------------------------------------------------------

    duplicates = company_ids[
        company_ids.duplicated(keep=False)
    ]

    for company_id in duplicates.unique():

        issues.append(
            create_issue(
                "DQ-01",
                "CRITICAL",
                "companies",
                company_id=company_id,
                field="id",
                message="Duplicate company primary key",
                raw_value=company_id
            )
        )

    company_set = set(company_ids)

    # ---------------------------------------------------------
    # DQ-02 / DQ-03 / DQ-07 / DQ-08
    # ---------------------------------------------------------

    annual_tables = [
        "profitandloss",
        "balancesheet",
        "cashflow"
    ]

    for table_name in annual_tables:

        df = frames[table_name].copy()

        df["company_id"] = (
            df["company_id"]
            .map(normalize_ticker)
        )

        # DQ-02
        duplicate_groups = (
            df.groupby(
                ["company_id", "year"],
                dropna=False
            )
            .size()
        )

        duplicate_groups = duplicate_groups[
            duplicate_groups > 1
        ]

        for key, count in duplicate_groups.items():

            company_id, year = key

            issues.append(
                create_issue(
                    "DQ-02",
                    "CRITICAL",
                    table_name,
                    company_id,
                    year,
                    "company_id,year",
                    "Duplicate annual key",
                    int(count)
                )
            )

        # Row-level validation
        for _, row in df.iterrows():

            company_id = normalize_ticker(
                row["company_id"]
            )

            raw_year = row.get("year", "")

            # DQ-03
            if company_id not in company_set:

                issues.append(
                    create_issue(
                        "DQ-03",
                        "CRITICAL",
                        table_name,
                        company_id,
                        raw_year,
                        "company_id",
                        "Orphan company_id",
                        company_id
                    )
                )

            # DQ-07
            try:

                normalize_year(raw_year)

            except Exception:

                issues.append(
                    create_issue(
                        "DQ-07",
                        "CRITICAL",
                        table_name,
                        company_id,
                        raw_year,
                        "year",
                        "Unparseable year",
                        raw_year
                    )
                )

            # DQ-08
            if not 2 <= len(company_id) <= 12:

                issues.append(
                    create_issue(
                        "DQ-08",
                        "CRITICAL",
                        table_name,
                        company_id,
                        raw_year,
                        "company_id",
                        "Ticker length outside 2-12 characters",
                        company_id
                    )
                )

    # ---------------------------------------------------------
    # DQ-04 Balance Sheet Balance
    # ---------------------------------------------------------

    bs = frames["balancesheet"].copy()

    if {
        "total_assets",
        "total_liabilities"
    }.issubset(bs.columns):

        denominator = (
            bs["total_assets"]
            .replace(0, np.nan)
        )

        difference = (
            (
                bs["total_assets"]
                - bs["total_liabilities"]
            )
            .abs()
            / denominator
        )

        for index in bs.index[
            difference >= 0.01
        ]:

            row = bs.loc[index]

            issues.append(
                create_issue(
                    "DQ-04",
                    "WARNING",
                    "balancesheet",
                    row.get("company_id"),
                    row.get("year"),
                    "total_assets",
                    "Assets/liabilities imbalance >= 1%",
                    float(difference.loc[index])
                )
            )

    # ---------------------------------------------------------
    # DQ-05 OPM Cross Check
    # ---------------------------------------------------------

    pl = frames["profitandloss"].copy()

    required_columns = {
        "sales",
        "operating_profit",
        "opm_percentage"
    }

    if required_columns.issubset(pl.columns):

        calculated_opm = np.where(
            pl["sales"] != 0,
            pl["operating_profit"]
            / pl["sales"]
            * 100,
            np.nan
        )

        difference = (
            pl["opm_percentage"]
            - calculated_opm
        ).abs()

        for index in pl.index[
            (difference >= 1)
            & np.isfinite(difference)
        ]:

            row = pl.loc[index]

            issues.append(
                create_issue(
                    "DQ-05",
                    "WARNING",
                    "profitandloss",
                    row.get("company_id"),
                    row.get("year"),
                    "opm_percentage",
                    "Source OPM differs from computed OPM by >= 1 percentage point",
                    float(difference.loc[index])
                )
            )

    # ---------------------------------------------------------
    # DQ-06 Positive Sales
    # ---------------------------------------------------------

    if "sales" in pl.columns:

        sector_map = {}

        if {
            "company_id",
            "broad_sector"
        }.issubset(frames["sectors"].columns):

            sector_map = dict(
                zip(
                    frames["sectors"]["company_id"]
                    .map(normalize_ticker),
                    frames["sectors"]["broad_sector"]
                )
            )

        for index in pl.index[
            pl["sales"] <= 0
        ]:

            row = pl.loc[index]

            company_id = normalize_ticker(
                row.get("company_id")
            )

            sector = sector_map.get(company_id)

            if sector not in BANK_TERMS:

                issues.append(
                    create_issue(
                        "DQ-06",
                        "WARNING",
                        "profitandloss",
                        company_id,
                        row.get("year"),
                        "sales",
                        "Sales <= 0 for non-financial company",
                        row.get("sales")
                    )
                )

    # ---------------------------------------------------------
    # DQ-09 Net Cash Flow
    # ---------------------------------------------------------

    cf = frames["cashflow"].copy()

    cashflow_columns = {
        "operating_activity",
        "investing_activity",
        "financing_activity",
        "net_cash_flow"
    }

    if cashflow_columns.issubset(cf.columns):

        calculated_cashflow = (
            cf[
                [
                    "operating_activity",
                    "investing_activity",
                    "financing_activity"
                ]
            ]
            .fillna(0)
            .sum(axis=1)
        )

        difference = (
            cf["net_cash_flow"]
            - calculated_cashflow
        ).abs()

        for index in cf.index[
            difference > 10
        ]:

            row = cf.loc[index]

            issues.append(
                create_issue(
                    "DQ-09",
                    "WARNING",
                    "cashflow",
                    row.get("company_id"),
                    row.get("year"),
                    "net_cash_flow",
                    "Net cash differs from CFO + CFI + CFF by > 10 Cr",
                    float(difference.loc[index])
                )
            )

    # ---------------------------------------------------------
    # DQ-10 Fixed Assets
    # ---------------------------------------------------------

    if "fixed_assets" in bs.columns:

        for index in bs.index[
            bs["fixed_assets"] < 0
        ]:

            row = bs.loc[index]

            issues.append(
                create_issue(
                    "DQ-10",
                    "WARNING",
                    "balancesheet",
                    row.get("company_id"),
                    row.get("year"),
                    "fixed_assets",
                    "Negative fixed assets",
                    row.get("fixed_assets")
                )
            )

    # ---------------------------------------------------------
    # DQ-11 Tax Rate
    # ---------------------------------------------------------

    if "tax_percentage" in pl.columns:

        mask = (
            (pl["tax_percentage"] < 0)
            |
            (pl["tax_percentage"] > 60)
        )

        for index in pl.index[mask]:

            row = pl.loc[index]

            issues.append(
                create_issue(
                    "DQ-11",
                    "WARNING",
                    "profitandloss",
                    row.get("company_id"),
                    row.get("year"),
                    "tax_percentage",
                    "Tax rate outside 0-60%",
                    row.get("tax_percentage")
                )
            )

    # ---------------------------------------------------------
    # DQ-12 Dividend Payout
    # ---------------------------------------------------------

    if "dividend_payout" in pl.columns:

        for index in pl.index[
            pl["dividend_payout"] > 200
        ]:

            row = pl.loc[index]

            issues.append(
                create_issue(
                    "DQ-12",
                    "WARNING",
                    "profitandloss",
                    row.get("company_id"),
                    row.get("year"),
                    "dividend_payout",
                    "Dividend payout > 200%",
                    row.get("dividend_payout")
                )
            )

    # ---------------------------------------------------------
    # DQ-13 Annual Report URL
    # ---------------------------------------------------------

    if "Annual_Report" in frames["documents"].columns:

        documents = frames["documents"]

    else:

        documents = frames["documents"].rename(
            columns={
                "annual_report": "Annual_Report"
            }
        )

    for _, row in documents.iterrows():

        url = str(
            row.get("Annual_Report", "")
        ).strip()

        if (
            not url
            or url.lower() in {"nan", "null"}
        ):

            issues.append(
                create_issue(
                    "DQ-13",
                    "WARNING",
                    "documents",
                    row.get("company_id"),
                    row.get("year"),
                    "Annual_Report",
                    "Missing annual report URL",
                    url
                )
            )

        elif not re.match(
            r"^https?://",
            url
        ):

            issues.append(
                create_issue(
                    "DQ-13",
                    "WARNING",
                    "documents",
                    row.get("company_id"),
                    row.get("year"),
                    "Annual_Report",
                    "Invalid URL syntax",
                    url
                )
            )

    # ---------------------------------------------------------
    # DQ-14 EPS Sign Consistency
    # ---------------------------------------------------------

    if {
        "net_profit",
        "eps"
    }.issubset(pl.columns):

        mask = (
            (pl["net_profit"] > 0)
            &
            (pl["eps"] <= 0)
        )

        for index in pl.index[mask]:

            row = pl.loc[index]

            issues.append(
                create_issue(
                    "DQ-14",
                    "WARNING",
                    "profitandloss",
                    row.get("company_id"),
                    row.get("year"),
                    "eps",
                    "EPS <= 0 while net profit > 0",
                    row.get("eps")
                )
            )

    # ---------------------------------------------------------
    # DQ-15 Strict Balance
    # ---------------------------------------------------------

    if {
        "total_assets",
        "total_liabilities"
    }.issubset(bs.columns):

        mask = (
            bs["total_assets"]
            != bs["total_liabilities"]
        )

        for index in bs.index[mask]:

            row = bs.loc[index]

            issues.append(
                create_issue(
                    "DQ-15",
                    "INFO",
                    "balancesheet",
                    row.get("company_id"),
                    row.get("year"),
                    "total_assets",
                    "Strict asset/liability equality check",
                    float(
                        row["total_assets"]
                        - row["total_liabilities"]
                    )
                )
            )
    # ---------------------------------------------------------
    # DQ-16 Coverage Check
    # ---------------------------------------------------------

    for company_id in sorted(company_set):

        for table_name in [
            "profitandloss",
            "balancesheet",
            "cashflow"
        ]:

            df = frames[table_name]

            company_rows = df[
                df["company_id"]
                .map(normalize_ticker)
                == company_id
            ]

            years = set()

            for year in company_rows["year"]:

                try:

                    years.add(
                        normalize_year(year)
                    )

                except Exception:

                    pass

            count = len(years)

            if count < 5:

                issues.append(
                    create_issue(
                        "DQ-16",
                        "WARNING",
                        table_name,
                        company_id,
                        None,
                        "year",
                        f"Coverage below 5 years: {count}",
                        count
                    )
                )

    return pd.DataFrame(
        issues,
        columns=[
            "rule_id",
            "severity",
            "table",
            "company_id",
            "year",
            "field",
            "issue",
            "raw_value"
        ]
    )