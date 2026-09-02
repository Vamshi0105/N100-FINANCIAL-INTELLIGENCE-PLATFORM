import numpy as np
import pandas as pd


# ---------------------------------------------------------------------
# WEIGHTS
# ---------------------------------------------------------------------

WEIGHTS = {
    # Profitability = 35%
    "roe": 15,
    "roce": 10,
    "npm": 10,

    # Cash Quality = 30%
    "fcf_cagr": 15,
    "cfo_pat": 10,
    "fcf_positive": 5,

    # Growth = 20%
    "revenue_cagr": 10,
    "pat_cagr": 10,

    # Leverage = 15%
    "debt_to_equity": 10,
    "interest_coverage": 5,
}


# ---------------------------------------------------------------------
# NORMALISATION
# ---------------------------------------------------------------------

def winsorised_score(series: pd.Series) -> pd.Series:
    """
    Convert a metric to a 0-100 score using P10/P90 winsorisation.

    Values below P10 are capped at P10.
    Values above P90 are capped at P90.
    """

    series = pd.to_numeric(series, errors="coerce")

    result = pd.Series(
        np.nan,
        index=series.index,
        dtype=float,
    )

    valid = series.dropna()

    if valid.empty:
        return result

    p10 = valid.quantile(0.10)
    p90 = valid.quantile(0.90)

    # Avoid division by zero for constant series
    if pd.isna(p10) or pd.isna(p90) or p10 == p90:
        result.loc[valid.index] = 50.0
        return result

    capped = series.clip(
        lower=p10,
        upper=p90,
    )

    result = (
        (capped - p10)
        / (p90 - p10)
        * 100
    )

    return result.clip(0, 100)


def inverse_winsorised_score(series: pd.Series) -> pd.Series:
    """
    Score metrics where LOWER is better.

    Used for Debt-to-Equity.
    """

    score = winsorised_score(series)

    return 100 - score


# ---------------------------------------------------------------------
# FCF CAGR
# ---------------------------------------------------------------------

def calculate_fcf_cagr_5yr(dataframe: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate 5-year FCF CAGR for each company.

    CAGR is calculated only where both start and end
    Free Cash Flow values are positive.
    """

    df = dataframe.copy()

    df["year_numeric"] = pd.to_datetime(
        df["year"].astype(str),
        errors="coerce",
    )

    df = df.sort_values(
        ["company_id", "year_numeric"]
    )

    df["fcf_cagr_5yr"] = np.nan

    for company_id, group in df.groupby("company_id"):

        group = group.sort_values("year_numeric")

        for index, row in group.iterrows():

            current_date = row["year_numeric"]

            if pd.isna(current_date):
                continue

            current_fcf = row["free_cash_flow_cr"]

            if (
                pd.isna(current_fcf)
                or current_fcf <= 0
            ):
                continue

            target_date = (
                current_date
                - pd.DateOffset(years=5)
            )

            historical = group[
                group["year_numeric"] <= target_date
            ]

            if historical.empty:
                continue

            start_row = historical.iloc[-1]

            start_fcf = (
                start_row["free_cash_flow_cr"]
            )

            if (
                pd.isna(start_fcf)
                or start_fcf <= 0
            ):
                continue

            years = (
                current_date.year
                - start_row["year_numeric"].year
            )

            if years <= 0:
                continue

            cagr = (
                (
                    current_fcf
                    / start_fcf
                )
                ** (1 / years)
                - 1
            ) * 100

            df.loc[
                index,
                "fcf_cagr_5yr"
            ] = cagr

    return df.drop(
        columns=["year_numeric"]
    )


# ---------------------------------------------------------------------
# SECTOR RELATIVE SCORING
# ---------------------------------------------------------------------

def calculate_sector_scores(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Calculate P10/P90 normalised scores within each broad sector.
    """

    df = dataframe.copy()

    metrics = {
        "roe_score": (
            "return_on_equity_pct",
            False,
        ),
        "roce_score": (
            "return_on_capital_employed_pct",
            False,
        ),
        "npm_score": (
            "net_profit_margin_pct",
            False,
        ),
        "fcf_cagr_score": (
            "fcf_cagr_5yr",
            False,
        ),
        "cfo_pat_score": (
            "cfo_quality_ratio",
            False,
        ),
        "revenue_cagr_score": (
            "revenue_cagr_5yr",
            False,
        ),
        "pat_cagr_score": (
            "pat_cagr_5yr",
            False,
        ),
        "debt_to_equity_score": (
            "debt_to_equity",
            True,
        ),
        "interest_coverage_score": (
            "interest_coverage",
            False,
        ),
    }

    for score_column in metrics:
        df[score_column] = np.nan

    # Score each sector independently
    for sector, sector_index in (
        df.groupby("broad_sector").groups.items()
    ):

        sector_df = df.loc[
            sector_index
        ]

        for score_column, (
            metric_column,
            inverse,
        ) in metrics.items():

            if metric_column not in sector_df.columns:
                continue

            if inverse:
                scores = inverse_winsorised_score(
                    sector_df[metric_column]
                )
            else:
                scores = winsorised_score(
                    sector_df[metric_column]
                )

            df.loc[
                sector_index,
                score_column,
            ] = scores

    return df


# ---------------------------------------------------------------------
# COMPOSITE SCORE
# ---------------------------------------------------------------------

def calculate_composite_quality_score(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Calculate the complete 0-100 composite quality score.

    Scoring is sector-relative.
    """

    df = dataframe.copy()

    # Calculate FCF CAGR
    df = calculate_fcf_cagr_5yr(df)

    # Calculate sector-relative metric scores
    df = calculate_sector_scores(df)

    # FCF positive score
    df["fcf_positive_score"] = np.where(
        df["free_cash_flow_cr"] > 0,
        100.0,
        0.0,
    )

    # Debt-free ICR handling
    icr_numeric = pd.to_numeric(
        df["interest_coverage"],
        errors="coerce",
    )

    debt_free = (
        df["icr_label"]
        .astype(str)
        .str.lower()
        .eq("debt free")
    )

    # Debt free companies receive 100 for ICR
    df.loc[
        debt_free,
        "interest_coverage_score",
    ] = 100.0

    # Weighted total
    weighted_columns = {
        "roe_score": WEIGHTS["roe"],
        "roce_score": WEIGHTS["roce"],
        "npm_score": WEIGHTS["npm"],
        "fcf_cagr_score": WEIGHTS["fcf_cagr"],
        "cfo_pat_score": WEIGHTS["cfo_pat"],
        "fcf_positive_score": WEIGHTS["fcf_positive"],
        "revenue_cagr_score": WEIGHTS["revenue_cagr"],
        "pat_cagr_score": WEIGHTS["pat_cagr"],
        "debt_to_equity_score": WEIGHTS[
            "debt_to_equity"
        ],
        "interest_coverage_score": WEIGHTS[
            "interest_coverage"
        ],
    }

    # Missing metrics contribute zero.
    composite = pd.Series(
        0.0,
        index=df.index,
    )

    for column, weight in (
        weighted_columns.items()
    ):

        values = (
            df[column]
            .fillna(0)
        )

        composite += (
            values * weight / 100
        )

    df[
        "composite_quality_score"
    ] = composite.clip(
        lower=0,
        upper=100,
    )

    return df