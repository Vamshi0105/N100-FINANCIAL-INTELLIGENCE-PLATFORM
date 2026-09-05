from __future__ import annotations

import math
import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "nifty100.db"

DEFAULT_OUTPUT_DIR = (
    PROJECT_ROOT
    / "reports"
    / "radar_charts"
)


# These 7 metrics already have percentile rankings
# from Day 18.
PEER_METRICS = [
    ("ROE", "ROE"),
    ("ROCE", "ROCE"),
    ("NPM", "Net Profit Margin"),
    ("D/E", "D/E"),
    ("FCF Score", "FCF"),
    ("PAT CAGR 5yr", "PAT CAGR 5yr"),
    ("Revenue CAGR 5yr", "Revenue CAGR 5yr"),
]


AXES = [
    "ROE",
    "ROCE",
    "NPM",
    "D/E",
    "FCF Score",
    "PAT CAGR 5yr",
    "Revenue CAGR 5yr",
    "Composite Score",
]


def get_latest_annual_year(
    connection: sqlite3.Connection,
) -> str:
    """
    Return the latest annual reporting period.

    Example:
        2024-03
    """

    row = connection.execute(
        """
        SELECT MAX(year)
        FROM peer_percentiles
        WHERE year LIKE '%-03'
        """
    ).fetchone()

    if row is None or row[0] is None:
        raise ValueError(
            "No annual peer percentile data found."
        )

    return str(row[0])


def load_peer_percentile_data(
    connection: sqlite3.Connection,
    year: str,
) -> pd.DataFrame:
    """
    Load Day 18 percentile rankings.
    """

    query = """
        SELECT
            company_id,
            peer_group_name,
            metric,
            value,
            percentile_rank,
            year
        FROM peer_percentiles
        WHERE year = ?
    """

    df = pd.read_sql_query(
        query,
        connection,
        params=(year,),
    )

    if df.empty:
        return df

    df["company_id"] = (
        df["company_id"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    return df


def load_composite_scores(
    connection: sqlite3.Connection,
    year: str,
) -> pd.DataFrame:
    """
    Load composite quality scores from financial_ratios.
    """

    query = """
        SELECT
            company_id,
            year,
            composite_quality_score
        FROM financial_ratios
        WHERE year = ?
    """

    df = pd.read_sql_query(
        query,
        connection,
        params=(year,),
    )

    if df.empty:
        return df

    df["company_id"] = (
        df["company_id"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    return df


def load_all_companies(
    connection: sqlite3.Connection,
) -> pd.DataFrame:
    """
    Load all companies from the companies table.
    """

    query = """
        SELECT
            id AS company_id,
            company_name
        FROM companies
    """

    df = pd.read_sql_query(
        query,
        connection,
    )

    df["company_id"] = (
        df["company_id"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    return df


def normalise_composite_scores(
    composite_df: pd.DataFrame,
    peer_mapping: pd.DataFrame,
) -> pd.DataFrame:
    """
    Normalise Composite Score within each peer group
    using min-max scaling.

    Result range:
        0.0 to 1.0

    If all companies in a peer group have the same
    composite score, assign 1.0.
    """

    df = composite_df.copy()

    peers = peer_mapping[
        [
            "company_id",
            "peer_group_name",
        ]
    ].drop_duplicates()

    df = df.merge(
        peers,
        on="company_id",
        how="left",
    )

    df["composite_normalised"] = np.nan

    grouped = df.groupby(
        "peer_group_name",
        dropna=True,
    )

    for group_name, indexes in grouped.groups.items():

        values = df.loc[
            indexes,
            "composite_quality_score",
        ]

        valid_values = values.dropna()

        if valid_values.empty:
            continue

        minimum = valid_values.min()
        maximum = valid_values.max()

        if maximum == minimum:

            df.loc[
                indexes,
                "composite_normalised",
            ] = 1.0

        else:

            df.loc[
                indexes,
                "composite_normalised",
            ] = (
                (
                    df.loc[
                        indexes,
                        "composite_quality_score",
                    ]
                    - minimum
                )
                /
                (maximum - minimum)
            )

    return df


def build_radar_dataset(
    peer_df: pd.DataFrame,
    composite_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Combine the 7 peer percentile metrics with the
    normalised Composite Score.

    Returns one row per company.
    """

    if peer_df.empty:
        return pd.DataFrame(
            columns=[
                "company_id",
                "peer_group_name",
                *AXES,
            ]
        )

    peer_mapping = peer_df[
        [
            "company_id",
            "peer_group_name",
        ]
    ].drop_duplicates()

    composite_normalised = (
        normalise_composite_scores(
            composite_df,
            peer_mapping,
        )
    )

    rows = []

    companies = (
        peer_df[
            [
                "company_id",
                "peer_group_name",
            ]
        ]
        .drop_duplicates()
    )

    for row in companies.itertuples(index=False):

        company_id = row.company_id
        peer_group_name = row.peer_group_name

        company_metrics = peer_df[
            (
                peer_df["company_id"]
                == company_id
            )
            &
            (
                peer_df["peer_group_name"]
                == peer_group_name
            )
        ]

        result_row = {
            "company_id": company_id,
            "peer_group_name": peer_group_name,
        }

        for axis_name, metric_name in PEER_METRICS:

            metric_match = company_metrics[
                company_metrics["metric"]
                == metric_name
            ]

            if metric_match.empty:

                result_row[axis_name] = np.nan

            else:

                result_row[axis_name] = float(
                    metric_match.iloc[0][
                        "percentile_rank"
                    ]
                )

        composite_match = (
            composite_normalised[
                (
                    composite_normalised[
                        "company_id"
                    ]
                    == company_id
                )
                &
                (
                    composite_normalised[
                        "peer_group_name"
                    ]
                    == peer_group_name
                )
            ]
        )

        if composite_match.empty:

            result_row[
                "Composite Score"
            ] = np.nan

        else:

            result_row[
                "Composite Score"
            ] = composite_match.iloc[0][
                "composite_normalised"
            ]

        rows.append(result_row)

    return pd.DataFrame(rows)


def get_peer_group_average(
    radar_df: pd.DataFrame,
    peer_group_name: str,
) -> list[float]:
    """
    Calculate average normalised values
    for a peer group.
    """

    group_df = radar_df[
        radar_df["peer_group_name"]
        == peer_group_name
    ]

    averages = []

    for axis in AXES:

        value = group_df[
            axis
        ].mean()

        if pd.isna(value):
            value = 0.0

        averages.append(
            float(value)
        )

    return averages


def create_radar_chart(
    company_id: str,
    peer_group_name: str,
    company_values: list[float],
    peer_average_values: list[float],
    year: str,
    output_path: Path,
) -> None:
    """
    Create an 8-axis radar chart.

    Company:
        filled polygon

    Peer average:
        dashed outline
    """

    number_of_axes = len(AXES)

    angles = np.linspace(
        0,
        2 * np.pi,
        number_of_axes,
        endpoint=False,
    ).tolist()

    # Close the radar polygon.
    angles += angles[:1]

    company_values = [
        0.0
        if pd.isna(value)
        else float(value)
        for value in company_values
    ]

    peer_average_values = [
        0.0
        if pd.isna(value)
        else float(value)
        for value in peer_average_values
    ]

    company_values += company_values[:1]

    peer_average_values += (
        peer_average_values[:1]
    )

    fig, ax = plt.subplots(
        figsize=(10, 10),
        subplot_kw={
            "polar": True,
        },
    )

    ax.set_theta_offset(
        np.pi / 2
    )

    ax.set_theta_direction(
        -1
    )

    ax.set_xticks(
        angles[:-1]
    )

    ax.set_xticklabels(
        AXES,
        fontsize=11,
        fontweight="bold",
    )

    ax.set_ylim(
        0,
        1,
    )

    ax.set_yticks(
        [0.2, 0.4, 0.6, 0.8, 1.0]
    )

    ax.set_yticklabels(
        [
            "0.2",
            "0.4",
            "0.6",
            "0.8",
            "1.0",
        ],
        fontsize=9,
    )

    ax.plot(
        angles,
        company_values,
        linewidth=2.5,
        marker="o",
        label=company_id,
    )

    ax.fill(
        angles,
        company_values,
        alpha=0.25,
    )

    ax.plot(
        angles,
        peer_average_values,
        linewidth=2.0,
        linestyle="--",
        marker="s",
        label=(
            "Peer Group Average"
        ),
    )

    ax.set_title(
        (
            f"{company_id} — Financial Profile\n"
            f"Peer Group: {peer_group_name} | "
            f"Year: {year}"
        ),
        fontsize=16,
        fontweight="bold",
        pad=30,
    )

    ax.legend(
        loc="upper right",
        bbox_to_anchor=(
            1.30,
            1.15,
        ),
        fontsize=11,
    )

    fig.text(
        0.5,
        0.03,
        (
            "Values are normalised from 0 to 1 "
            "within the peer group. "
            "Higher values represent stronger "
            "relative performance."
        ),
        ha="center",
        fontsize=9,
    )

    plt.tight_layout(
        rect=[
            0,
            0.06,
            1,
            1,
        ]
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    plt.savefig(
        output_path,
        dpi=150,
        bbox_inches="tight",
    )

    plt.close(fig)


def create_standalone_chart(
    company_id: str,
    company_score: float,
    nifty_average: float,
    year: str,
    output_path: Path,
) -> None:
    """
    Create a standalone chart for a company
    without a peer group.

    Uses Composite Score compared against the
    Nifty 100 average.
    """

    fig, ax = plt.subplots(
        figsize=(8, 6),
    )

    labels = [
        company_id,
        "Nifty 100 Average",
    ]

    values = [
        company_score,
        nifty_average,
    ]

    bars = ax.bar(
        labels,
        values,
    )

    ax.set_ylabel(
        "Composite Quality Score",
        fontsize=12,
    )

    ax.set_title(
        (
            f"{company_id} — Standalone Financial Profile\n"
            f"No Peer Group Assigned | Year: {year}"
        ),
        fontsize=15,
        fontweight="bold",
    )

    ax.tick_params(
        axis="x",
        labelsize=11,
    )

    ax.tick_params(
        axis="y",
        labelsize=10,
    )

    for bar, value in zip(
        bars,
        values,
    ):

        if pd.notna(value):

            ax.text(
                bar.get_x()
                + bar.get_width() / 2,
                bar.get_height(),
                f"{value:.2f}",
                ha="center",
                va="bottom",
                fontsize=11,
            )

    fig.text(
        0.5,
        0.03,
        (
            "Company has no peer group assignment. "
            "Nifty 100 average is shown as reference."
        ),
        ha="center",
        fontsize=9,
    )

    plt.tight_layout(
        rect=[
            0,
            0.06,
            1,
            1,
        ]
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    plt.savefig(
        output_path,
        dpi=150,
        bbox_inches="tight",
    )

    plt.close(fig)


def generate_radar_charts(
    db_path: str | Path = DEFAULT_DB_PATH,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> int:
    """
    Main Day 19 workflow.

    1. Select latest annual year.
    2. Load Day 18 peer percentiles.
    3. Load composite scores.
    4. Generate radar chart for every company
       with a peer group.
    5. Generate standalone chart for companies
       without a peer group.
    """

    db_path = Path(db_path)

    output_dir = Path(
        output_dir
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    with sqlite3.connect(
        db_path
    ) as connection:

        year = get_latest_annual_year(
            connection
        )

        peer_df = (
            load_peer_percentile_data(
                connection,
                year,
            )
        )

        composite_df = (
            load_composite_scores(
                connection,
                year,
            )
        )

        companies_df = (
            load_all_companies(
                connection
            )
        )

    radar_df = build_radar_dataset(
        peer_df,
        composite_df,
    )

    charts_created = 0

    # ----------------------------------
    # Companies with peer groups
    # ----------------------------------

    for row in radar_df.to_dict(
        orient="records"
    ):

        company_values = []

        for axis in AXES:

            value = row[axis]

            company_values.append(
                value
            )

        peer_average_values = (
            get_peer_group_average(
                radar_df,
                row["peer_group_name"],
            )
        )

        safe_company_id = (
            str(row["company_id"])
            .replace("/", "_")
            .replace("\\", "_")
        )

        output_path = (
            output_dir
            / f"{safe_company_id}_radar.png"
        )

        create_radar_chart(
            company_id=row["company_id"],
            peer_group_name=row["peer_group_name"],
            company_values=company_values,
            peer_average_values=(
                peer_average_values
            ),
            year=year,
            output_path=output_path,
        )

        charts_created += 1

    # ----------------------------------
    # Companies without peer groups
    # ----------------------------------

    peer_company_ids = set(
        radar_df[
            "company_id"
        ].astype(str)
    )

    standalone_companies = (
        companies_df[
            ~companies_df[
                "company_id"
            ].isin(
                peer_company_ids
            )
        ]
    )

    nifty_average = (
        composite_df[
            "composite_quality_score"
        ].mean()
    )

    for row in standalone_companies.itertuples(
        index=False
    ):

        score_match = composite_df[
            composite_df[
                "company_id"
            ]
            == row.company_id
        ]

        if score_match.empty:
            continue

        company_score = (
            score_match.iloc[0][
                "composite_quality_score"
            ]
        )

        if pd.isna(
            company_score
        ):
            continue

        safe_company_id = (
            str(row.company_id)
            .replace("/", "_")
            .replace("\\", "_")
        )

        output_path = (
            output_dir
            / f"{safe_company_id}_radar.png"
        )

        create_standalone_chart(
            company_id=row.company_id,
            company_score=float(
                company_score
            ),
            nifty_average=float(
                nifty_average
            ),
            year=year,
            output_path=output_path,
        )

        charts_created += 1

    return charts_created


if __name__ == "__main__":

    charts_created = (
        generate_radar_charts()
    )

    print(
        f"Radar charts created: "
        f"{charts_created}"
    )

    print(
        f"Output directory: "
        f"{DEFAULT_OUTPUT_DIR}"
    )