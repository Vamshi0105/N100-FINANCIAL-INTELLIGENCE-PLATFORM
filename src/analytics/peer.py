from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "nifty100.db"
DEFAULT_PEER_GROUPS_PATH = (
    PROJECT_ROOT / "data" / "supporting" / "peer_groups.xlsx"
)


# Metric name shown in peer_percentiles -> source column in financial_ratios
METRICS = {
    "ROE": "return_on_equity_pct",
    "ROCE": "return_on_capital_employed_pct",
    "Net Profit Margin": "net_profit_margin_pct",
    "D/E": "debt_to_equity",
    "FCF": "free_cash_flow_cr",
    "PAT CAGR 5yr": "pat_cagr_5yr",
    "Revenue CAGR 5yr": "revenue_cagr_5yr",
    "EPS CAGR 5yr": "eps_cagr_5yr",
    "Interest Coverage": "interest_coverage",
    "Asset Turnover": "asset_turnover",
}


def load_peer_groups(
    peer_groups_path: str | Path = DEFAULT_PEER_GROUPS_PATH,
) -> pd.DataFrame:
    """
    Load peer group assignments from peer_groups.xlsx.

    Returns columns:
        company_id
        peer_group_name
    """

    peer_groups_path = Path(peer_groups_path)

    if not peer_groups_path.exists():
        raise FileNotFoundError(
            f"Peer groups file not found: {peer_groups_path}"
        )

    df = pd.read_excel(peer_groups_path)

    required_columns = {
        "company_id",
        "peer_group_name",
    }

    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        raise ValueError(
            "peer_groups.xlsx is missing required columns: "
            + ", ".join(sorted(missing_columns))
        )

    df = df[
        ["company_id", "peer_group_name"]
    ].copy()

    df["company_id"] = (
        df["company_id"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    df["peer_group_name"] = (
        df["peer_group_name"]
        .astype(str)
        .str.strip()
    )

    df = df.drop_duplicates(
        subset=["company_id"],
        keep="first",
    )

    return df


def create_peer_percentiles_table(
    connection: sqlite3.Connection,
) -> None:
    """
    Create the peer_percentiles table if it does not already exist.
    """

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS peer_percentiles (
            company_id TEXT NOT NULL,
            peer_group_name TEXT NOT NULL,
            metric TEXT NOT NULL,
            value REAL,
            percentile_rank REAL,
            year  TEXT NOT NULL,
            PRIMARY KEY (
                company_id,
                peer_group_name,
                metric,
                year
            )
        )
        """
    )

    connection.commit()


def _normalise_company_id(
    series: pd.Series,
) -> pd.Series:
    """
    Convert company IDs into a consistent format for joins.
    """

    return (
        series.astype(str)
        .str.strip()
        .str.upper()
    )


def _get_financial_ratios(
    connection: sqlite3.Connection,
    year: Optional[str] = None,
) -> pd.DataFrame:
    """
    Load the required financial ratio metrics.

    If year is supplied, load that year.

    If year is None, load the latest annual reporting
    period (March year-end, YYYY-03). This provides
    the broadest comparable company coverage for
    peer percentile rankings.
    """

    metric_columns = ", ".join(METRICS.values())

    if year is None:

        query = f"""
            SELECT
                company_id,
                year,
                {metric_columns}
            FROM financial_ratios
            WHERE year = (
                SELECT MAX(year)
                FROM financial_ratios
                WHERE year LIKE '%-03'
            )
        """

        df = pd.read_sql_query(
            query,
            connection,
        )

    else:

        query = f"""
            SELECT
                company_id,
                year,
                {metric_columns}
            FROM financial_ratios
            WHERE year = ?
        """

        df = pd.read_sql_query(
            query,
            connection,
            params=(str(year),),
        )

    if df.empty:
        return df

    df["company_id"] = _normalise_company_id(
        df["company_id"]
    )

    return df


def calculate_peer_percentiles(
    ratios_df: pd.DataFrame,
    peer_groups_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Calculate percentile rankings for all metrics within each peer group.

    Percentile ranking formula is equivalent to SQL/PERCENT_RANK:

        (rank - 1) / (number_of_values - 1)

    Higher values are better for all metrics except D/E.

    For D/E:
        inverse percentile = 1 - percentile_rank

    Companies without a peer group are excluded from the ranking output.
    """

    if ratios_df.empty:
        return pd.DataFrame(
            columns=[
                "company_id",
                "peer_group_name",
                "metric",
                "value",
                "percentile_rank",
                "year",
            ]
        )

    ratios = ratios_df.copy()
    peers = peer_groups_df.copy()

    ratios["company_id"] = _normalise_company_id(
        ratios["company_id"]
    )

    peers["company_id"] = _normalise_company_id(
        peers["company_id"]
    )

    merged = ratios.merge(
        peers,
        on="company_id",
        how="left",
    )

    # Companies without a peer group are not ranked.
    merged = merged[
        merged["peer_group_name"].notna()
    ].copy()

    if merged.empty:
        return pd.DataFrame(
            columns=[
                "company_id",
                "peer_group_name",
                "metric",
                "value",
                "percentile_rank",
                "year",
            ]
        )

    results = []

    for metric_name, source_column in METRICS.items():

        metric_df = merged[
            [
                "company_id",
                "peer_group_name",
                "year",
                source_column,
            ]
        ].copy()

        metric_df = metric_df.rename(
            columns={
                source_column: "value",
            }
        )

        # Ignore missing metric values.
        metric_df = metric_df[
            metric_df["value"].notna()
        ].copy()

        if metric_df.empty:
            continue

        # pandas pct=False ranking gives standard rank.
        metric_df["rank"] = (
            metric_df
            .groupby("peer_group_name")["value"]
            .rank(
                method="min",
                ascending=True,
            )
        )

        metric_df["group_size"] = (
            metric_df
            .groupby("peer_group_name")["value"]
            .transform("count")
        )

        # Equivalent to PERCENT_RANK:
        #
        # (rank - 1) / (N - 1)
        metric_df["percentile_rank"] = (
            (metric_df["rank"] - 1)
            /
            (metric_df["group_size"] - 1)
        )

        # If only one company has a valid value
        # in a peer group, define percentile as 1.0.
        metric_df.loc[
            metric_df["group_size"] == 1,
            "percentile_rank",
        ] = 1.0

        # Lower D/E is better.
        if metric_name == "D/E":
            metric_df["percentile_rank"] = (
                1.0 - metric_df["percentile_rank"]
            )

        metric_df["metric"] = metric_name

        results.append(
            metric_df[
                [
                    "company_id",
                    "peer_group_name",
                    "metric",
                    "value",
                    "percentile_rank",
                    "year",
                ]
            ]
        )

    if not results:

        return pd.DataFrame(
            columns=[
                "company_id",
                "peer_group_name",
                "metric",
                "value",
                "percentile_rank",
                "year",
            ]
        )

    result = pd.concat(
        results,
        ignore_index=True,
    )

    result = result.sort_values(
        by=[
            "peer_group_name",
            "metric",
            "percentile_rank",
            "company_id",
        ],
        ascending=[
            True,
            True,
            False,
            True,
        ],
    )

    return result.reset_index(drop=True)


def save_peer_percentiles(
    connection: sqlite3.Connection,
    percentiles_df: pd.DataFrame,
) -> int:
    """
    Save percentile rankings into SQLite.

    Existing rows for the same company, group,
    metric and year are replaced.
    """

    if percentiles_df.empty:
        return 0

    rows = [
        (
            str(row.company_id),
            str(row.peer_group_name),
            str(row.metric),
            float(row.value),
            float(row.percentile_rank),
            str(row.year),
        )
        for row in percentiles_df.itertuples(
            index=False
        )
    ]

    connection.executemany(
        """
        INSERT OR REPLACE INTO peer_percentiles (
            company_id,
            peer_group_name,
            metric,
            value,
            percentile_rank,
            year
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        rows,
    )

    connection.commit()

    return len(rows)


def get_peer_group_for_company(
    company_id: str,
    peer_groups_df: pd.DataFrame,
) -> str:
    """
    Return the peer group for a company.

    If no group exists:
        'No peer group assigned'

    No exception is raised.
    """

    normalised_company_id = (
        str(company_id)
        .strip()
        .upper()
    )

    match = peer_groups_df[
        peer_groups_df["company_id"]
        == normalised_company_id
    ]

    if match.empty:
        return "No peer group assigned"

    return str(
        match.iloc[0]["peer_group_name"]
    )


def run_peer_percentile_ranking(
    db_path: str | Path = DEFAULT_DB_PATH,
    peer_groups_path: str | Path = DEFAULT_PEER_GROUPS_PATH,
    year: Optional[str] = None,
) -> pd.DataFrame:
    """
    Complete Day 18 workflow.

    1. Load peer_groups.xlsx
    2. Load financial ratio metrics
    3. Calculate percentile ranks within peer groups
    4. Invert D/E percentile
    5. Save results to SQLite
    """

    db_path = Path(db_path)

    peer_groups_df = load_peer_groups(
        peer_groups_path
    )

    with sqlite3.connect(db_path) as connection:

        create_peer_percentiles_table(
            connection
        )

        ratios_df = _get_financial_ratios(
            connection,
            year=year,
        )

        percentiles_df = calculate_peer_percentiles(
            ratios_df,
            peer_groups_df,
        )

        save_peer_percentiles(
            connection,
            percentiles_df,
        )

    return percentiles_df


if __name__ == "__main__":

    result = run_peer_percentile_ranking()

    print(
        f"Peer percentile rankings created: "
        f"{len(result)}"
    )

    if not result.empty:

        print("\nPreview:")

        print(
            result.head(20).to_string(
                index=False
            )
        )