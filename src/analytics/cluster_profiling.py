"""
Day 37 — Cluster Profiling & Statistics

Outputs:
    output/cluster_profile.csv
    output/outlier_report.csv
    output/portfolio_stats.csv
    reports/correlation_heatmap.png

Tasks:
    1. Profile each KMeans cluster using mean and median
       of the five Day 36 clustering features.
    2. Review descriptive cluster archetype names and memberships.
    3. Generate Pearson correlation heatmap for 10 KPIs.
    4. Detect sector-relative outliers using |Z| > 3.
    5. Generate portfolio statistics:
       P10, P25, P50, P75, P90, Mean, Std.
"""

from pathlib import Path
import logging
import sqlite3

import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt


# =====================================================================
# CONFIGURATION
# =====================================================================

BASE_DIR = Path(__file__).resolve().parents[2]

DB_PATH = BASE_DIR / "data" / "nifty100.db"

CLUSTER_LABELS_PATH = (
    BASE_DIR / "output" / "cluster_labels.csv"
)

FCF_CASHFLOW_PATH = (
    BASE_DIR / "output" / "cashflow_intelligence.xlsx"
)

CLUSTER_PROFILE_PATH = (
    BASE_DIR / "output" / "cluster_profile.csv"
)

OUTLIER_REPORT_PATH = (
    BASE_DIR / "output" / "outlier_report.csv"
)

PORTFOLIO_STATS_PATH = (
    BASE_DIR / "output" / "portfolio_stats.csv"
)

CORRELATION_HEATMAP_PATH = (
    BASE_DIR / "reports" / "correlation_heatmap.png"
)

EXPECTED_COMPANIES = 92


# =====================================================================
# KPI DEFINITIONS
# =====================================================================

# Five features used by Day 36 KMeans.
#
# fcf_cagr_5yr comes from cashflow_intelligence.xlsx,
# not financial_ratios.
CLUSTER_FEATURES = [
    "return_on_equity_pct",
    "debt_to_equity",
    "revenue_cagr_5yr",
    "fcf_cagr_5yr",
    "operating_profit_margin_pct",
]


# Ten KPIs required for Day 37.
#
# fcf_cagr_5yr is deliberately NOT included here because
# the Day 37 specification asks for 10 KPIs and the existing
# financial_ratios table contains these ten project KPIs.
CORRELATION_KPIS = [
    "net_profit_margin_pct",
    "operating_profit_margin_pct",
    "return_on_equity_pct",
    "return_on_capital_employed_pct",
    "return_on_assets_pct",
    "debt_to_equity",
    "interest_coverage",
    "asset_turnover",
    "dividend_payout_ratio_pct",
    "composite_quality_score",
]


# =====================================================================
# LOGGING
# =====================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


# =====================================================================
# HELPERS
# =====================================================================

def normalize_company_ids(
    series: pd.Series,
) -> pd.Series:
    """Normalize company identifiers."""

    return (
        series
        .astype(str)
        .str.strip()
        .str.upper()
    )


def ensure_directories() -> None:
    """Create required directories."""

    (BASE_DIR / "output").mkdir(
        parents=True,
        exist_ok=True,
    )

    (BASE_DIR / "reports").mkdir(
        parents=True,
        exist_ok=True,
    )


# =====================================================================
# LOAD OFFICIAL COMPANY UNIVERSE
# =====================================================================

def load_company_universe() -> pd.DataFrame:
    """
    Load the official 92-company universe.

    Actual companies table schema:
        id
        company_name
    """

    with sqlite3.connect(DB_PATH) as conn:

        df = pd.read_sql_query(
            """
            SELECT
                CAST(id AS TEXT) AS company_id,
                company_name
            FROM companies
            """,
            conn,
        )

    df["company_id"] = normalize_company_ids(
        df["company_id"]
    )

    df["company_name"] = (
        df["company_name"]
        .astype(str)
        .str.strip()
    )

    df = (
        df
        .drop_duplicates(
            subset=["company_id"]
        )
        .reset_index(drop=True)
    )

    logger.info(
        "Official company universe: %d",
        len(df),
    )

    if len(df) != EXPECTED_COMPANIES:

        raise ValueError(
            f"Expected {EXPECTED_COMPANIES} companies, "
            f"found {len(df)}"
        )

    return df


# =====================================================================
# LOAD LATEST FINANCIAL RATIOS
# =====================================================================

def load_latest_financial_data() -> pd.DataFrame:
    """
    Load latest financial-ratio record for each company.

    Annual YYYY-03 records are preferred.

    Companies without an annual YYYY-03 record fall back
    to their latest available financial record.
    """

    columns = [
        "company_id",
        "year",
        *CORRELATION_KPIS,
        "revenue_cagr_5yr",
    ]

    with sqlite3.connect(DB_PATH) as conn:

        df = pd.read_sql_query(
            f"""
            SELECT
                {", ".join(columns)}
            FROM financial_ratios
            """,
            conn,
        )

    df["company_id"] = normalize_company_ids(
        df["company_id"]
    )

    df["year"] = (
        df["year"]
        .astype(str)
        .str.strip()
    )

    # -------------------------------------------------------------
    # Annual YYYY-03 records
    # -------------------------------------------------------------

    annual = df[
        df["year"].str.match(
            r"^\d{4}-03$"
        )
    ].copy()

    if not annual.empty:

        annual["_year_num"] = (
            annual["year"]
            .str[:4]
            .astype(int)
        )

        annual = (
            annual
            .sort_values(
                [
                    "company_id",
                    "_year_num",
                ]
            )
            .groupby(
                "company_id",
                as_index=False,
            )
            .tail(1)
            .drop(
                columns="_year_num"
            )
        )

    annual_ids = set(
        annual["company_id"]
    )

    # -------------------------------------------------------------
    # Fallback for companies without YYYY-03 records
    # -------------------------------------------------------------

    fallback = df[
        ~df["company_id"].isin(
            annual_ids
        )
    ].copy()

    if not fallback.empty:

        logger.info(
            "Companies without annual YYYY-03 record: %d",
            fallback["company_id"].nunique(),
        )

        fallback["_year_sort"] = (
            fallback["year"]
            .str.extract(
                r"(\d{4})"
            )[0]
            .astype(float)
        )

        fallback = (
            fallback
            .sort_values(
                [
                    "company_id",
                    "_year_sort",
                ]
            )
            .groupby(
                "company_id",
                as_index=False,
            )
            .tail(1)
            .drop(
                columns="_year_sort"
            )
        )

    else:

        fallback = pd.DataFrame(
            columns=df.columns
        )

    latest = pd.concat(
        [
            annual,
            fallback,
        ],
        ignore_index=True,
    )

    latest = (
        latest
        .drop_duplicates(
            subset=["company_id"],
            keep="last",
        )
        .reset_index(drop=True)
    )

    logger.info(
        "Latest financial records retained: %d",
        latest["company_id"].nunique(),
    )

    return latest


# =====================================================================
# LOAD FCF CAGR FROM CASHFLOW INTELLIGENCE
# =====================================================================

def load_fcf_data() -> pd.DataFrame:
    """
    Load fcf_cagr_5yr from the Day 31 cash-flow intelligence output.

    This metric is not stored in financial_ratios.
    """

    if not FCF_CASHFLOW_PATH.exists():

        raise FileNotFoundError(
            "Missing required Day 31 output: "
            f"{FCF_CASHFLOW_PATH}"
        )

    logger.info(
        "Loading FCF CAGR data: %s",
        FCF_CASHFLOW_PATH,
    )

    df = pd.read_excel(
        FCF_CASHFLOW_PATH
    )

    required = {
        "company_id",
        "fcf_cagr_5yr",
    }

    missing = (
        required
        - set(df.columns)
    )

    if missing:

        raise ValueError(
            "cashflow_intelligence.xlsx missing "
            f"columns: {sorted(missing)}"
        )

    df = df[
        [
            "company_id",
            "fcf_cagr_5yr",
        ]
    ].copy()

    df["company_id"] = normalize_company_ids(
        df["company_id"]
    )

    df["fcf_cagr_5yr"] = pd.to_numeric(
        df["fcf_cagr_5yr"],
        errors="coerce",
    )

    df = (
        df
        .drop_duplicates(
            subset=["company_id"]
        )
        .reset_index(drop=True)
    )

    logger.info(
        "FCF CAGR companies loaded: %d",
        df["company_id"].nunique(),
    )

    return df


# =====================================================================
# LOAD SECTOR DATA
# =====================================================================

def load_sector_data() -> pd.DataFrame:
    """Load broad-sector assignments."""

    with sqlite3.connect(DB_PATH) as conn:

        sectors = pd.read_sql_query(
            """
            SELECT
                CAST(company_id AS TEXT) AS company_id,
                broad_sector
            FROM sectors
            """,
            conn,
        )

    sectors["company_id"] = normalize_company_ids(
        sectors["company_id"]
    )

    sectors["broad_sector"] = (
        sectors["broad_sector"]
        .astype(str)
        .str.strip()
    )

    sectors = (
        sectors[
            [
                "company_id",
                "broad_sector",
            ]
        ]
        .drop_duplicates(
            subset=["company_id"]
        )
        .reset_index(drop=True)
    )

    logger.info(
        "Sector assignments loaded: %d",
        len(sectors),
    )

    return sectors


# =====================================================================
# LOAD CLUSTER LABELS
# =====================================================================

def load_cluster_labels() -> pd.DataFrame:
    """Load validated Day 36 cluster labels."""

    if not CLUSTER_LABELS_PATH.exists():

        raise FileNotFoundError(
            "Missing Day 36 cluster output: "
            f"{CLUSTER_LABELS_PATH}"
        )

    df = pd.read_csv(
        CLUSTER_LABELS_PATH
    )

    required = {
        "company_id",
        "cluster_id",
        "cluster_name",
        "distance_from_centroid",
    }

    missing = (
        required
        - set(df.columns)
    )

    if missing:

        raise ValueError(
            "cluster_labels.csv missing "
            f"columns: {sorted(missing)}"
        )

    df["company_id"] = normalize_company_ids(
        df["company_id"]
    )

    if len(df) != EXPECTED_COMPANIES:

        raise ValueError(
            f"Expected {EXPECTED_COMPANIES} cluster labels, "
            f"found {len(df)}"
        )

    if (
        df["company_id"].nunique()
        != EXPECTED_COMPANIES
    ):

        raise ValueError(
            "Cluster labels do not contain "
            "92 unique companies."
        )

    logger.info(
        "Cluster labels loaded: %d companies",
        len(df),
    )

    return df


# =====================================================================
# BUILD MASTER DATASET
# =====================================================================

def build_master_dataset() -> pd.DataFrame:
    """
    Combine:

        official universe
        latest financial ratios
        FCF CAGR
        sector
        Day 36 cluster labels
    """

    universe = (
        load_company_universe()
    )

    financials = (
        load_latest_financial_data()
    )

    fcf = (
        load_fcf_data()
    )

    sectors = (
        load_sector_data()
    )

    clusters = (
        load_cluster_labels()
    )

    # -------------------------------------------------------------
    # Start from official universe.
    # -------------------------------------------------------------

    df = universe.merge(
        financials,
        on="company_id",
        how="left",
    )

    logger.info(
        "Companies after financial-data join: %d",
        len(df),
    )

    df = df.merge(
        fcf,
        on="company_id",
        how="left",
    )

    df = df.merge(
        sectors,
        on="company_id",
        how="left",
    )

    df = df.merge(
        clusters,
        on="company_id",
        how="left",
    )

    # -------------------------------------------------------------
    # Validate universe.
    # -------------------------------------------------------------

    if len(df) != EXPECTED_COMPANIES:

        raise ValueError(
            f"Master dataset expected "
            f"{EXPECTED_COMPANIES} rows, "
            f"found {len(df)}"
        )

    if (
        df["company_id"].nunique()
        != EXPECTED_COMPANIES
    ):

        raise ValueError(
            "Master dataset does not contain "
            "92 unique companies."
        )

    # -------------------------------------------------------------
    # Validate sectors.
    # -------------------------------------------------------------

    if df["broad_sector"].isna().any():

        missing = (
            df.loc[
                df["broad_sector"].isna(),
                "company_id",
            ]
            .tolist()
        )

        raise ValueError(
            "Missing sector assignments: "
            f"{missing}"
        )

    # -------------------------------------------------------------
    # Validate clusters.
    # -------------------------------------------------------------

    if df["cluster_id"].isna().any():

        missing = (
            df.loc[
                df["cluster_id"].isna(),
                "company_id",
            ]
            .tolist()
        )

        raise ValueError(
            "Missing cluster assignments: "
            f"{missing}"
        )

    logger.info(
        "Master Day 37 dataset: %d companies",
        len(df),
    )

    return df


# =====================================================================
# CLUSTER PROFILE
# =====================================================================

def generate_cluster_profile(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Compute mean and median of all five clustering
    features for every cluster.
    """

    logger.info(
        "Generating cluster profiles..."
    )

    rows = []

    cluster_ids = sorted(
        df["cluster_id"]
        .astype(int)
        .unique()
        .tolist()
    )

    for cluster_id in cluster_ids:

        subset = df[
            df["cluster_id"]
            .astype(int)
            == cluster_id
        ]

        cluster_name = (
            subset["cluster_name"]
            .mode()
            .iloc[0]
        )

        row = {
            "cluster_id": cluster_id,
            "cluster_name": cluster_name,
            "company_count": len(subset),
        }

        for feature in CLUSTER_FEATURES:

            values = pd.to_numeric(
                subset[feature],
                errors="coerce",
            )

            row[
                f"{feature}_mean"
            ] = values.mean()

            row[
                f"{feature}_median"
            ] = values.median()

        rows.append(row)

    profile = pd.DataFrame(
        rows
    )

    profile.to_csv(
        CLUSTER_PROFILE_PATH,
        index=False,
    )

    logger.info(
        "Cluster profile saved: %s",
        CLUSTER_PROFILE_PATH,
    )

    # -------------------------------------------------------------
    # Log detailed cluster statistics.
    # -------------------------------------------------------------

    logger.info(
        "Cluster profile summary:"
    )

    for _, row in profile.iterrows():

        logger.info(
            "  Cluster %d | %-22s | %d companies",
            int(row["cluster_id"]),
            row["cluster_name"],
            int(row["company_count"]),
        )

        for feature in CLUSTER_FEATURES:

            mean_value = row[
                f"{feature}_mean"
            ]

            median_value = row[
                f"{feature}_median"
            ]

            logger.info(
                "      %-32s mean=%10.3f median=%10.3f",
                feature,
                mean_value
                if pd.notna(mean_value)
                else np.nan,
                median_value
                if pd.notna(median_value)
                else np.nan,
            )

    return profile


# =====================================================================
# CLUSTER MEMBERSHIP REVIEW
# =====================================================================

def review_cluster_members(
    df: pd.DataFrame,
) -> None:
    """
    Print actual companies in every cluster.

    This supports manual/team-lead review of the
    descriptive archetype names.
    """

    logger.info(
        "Cluster company membership review:"
    )

    for cluster_id in sorted(
        df["cluster_id"]
        .astype(int)
        .unique()
        .tolist()
    ):

        subset = (
            df[
                df["cluster_id"]
                .astype(int)
                == cluster_id
            ]
            .sort_values(
                "company_name"
            )
        )

        name = (
            subset["cluster_name"]
            .mode()
            .iloc[0]
        )

        companies = ", ".join(
            subset[
                "company_name"
            ]
            .astype(str)
            .tolist()
        )

        logger.info(
            "  Cluster %d — %s",
            cluster_id,
            name,
        )

        logger.info(
            "      Companies (%d): %s",
            len(subset),
            companies,
        )


# =====================================================================
# CORRELATION HEATMAP
# =====================================================================

def generate_correlation_heatmap(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Generate Pearson correlation matrix for
    the ten Day 37 KPIs.
    """

    logger.info(
        "Generating Pearson correlation matrix..."
    )

    kpi_data = (
        df[
            CORRELATION_KPIS
        ]
        .apply(
            pd.to_numeric,
            errors="coerce",
        )
    )

    correlation = (
        kpi_data.corr(
            method="pearson"
        )
    )

    # -------------------------------------------------------------
    # Validate all ten KPIs exist.
    # -------------------------------------------------------------

    if (
        correlation.shape
        != (
            len(CORRELATION_KPIS),
            len(CORRELATION_KPIS),
        )
    ):

        raise ValueError(
            "Correlation matrix does not contain "
            "all 10 required KPIs."
        )

    # -------------------------------------------------------------
    # Generate annotated Seaborn heatmap.
    # -------------------------------------------------------------

    plt.figure(
        figsize=(14, 11)
    )

    sns.heatmap(
        correlation,
        annot=True,
        fmt=".2f",
        cmap="coolwarm",
        center=0,
        square=True,
        linewidths=0.5,
        cbar=True,
    )

    plt.title(
        "N100 Latest-Year KPI Pearson Correlation Matrix"
    )

    plt.xticks(
        rotation=45,
        ha="right",
    )

    plt.yticks(
        rotation=0,
    )

    plt.tight_layout()

    plt.savefig(
        CORRELATION_HEATMAP_PATH,
        dpi=200,
        bbox_inches="tight",
    )

    plt.close()

    logger.info(
        "Correlation heatmap saved: %s",
        CORRELATION_HEATMAP_PATH,
    )

    return correlation


# =====================================================================
# SECTOR-BASED OUTLIER DETECTION
# =====================================================================

def generate_outlier_report(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Calculate Z-score independently within each broad_sector.

    Flag companies where:

        abs(Z-score) > 3
    """

    logger.info(
        "Running sector-relative outlier detection..."
    )

    work = df[
        [
            "company_id",
            "company_name",
            "broad_sector",
            *CORRELATION_KPIS,
        ]
    ].copy()

    outlier_rows = []

    for sector, sector_df in work.groupby(
        "broad_sector",
        dropna=False,
    ):

        logger.info(
            "  Processing sector: %s (%d companies)",
            sector,
            len(sector_df),
        )

        for kpi in CORRELATION_KPIS:

            values = pd.to_numeric(
                sector_df[kpi],
                errors="coerce",
            )

            mean = values.mean()

            std = values.std(
                ddof=0
            )

            # -----------------------------------------------------
            # Zero standard deviation means every value is equal.
            # No observation can be an outlier in that metric.
            # -----------------------------------------------------

            if (
                pd.isna(std)
                or std == 0
            ):

                z_scores = pd.Series(
                    0.0,
                    index=sector_df.index,
                )

            else:

                z_scores = (
                    values - mean
                ) / std

            # -----------------------------------------------------
            # Flag |Z| > 3.
            # -----------------------------------------------------

            for idx, z_score in (
                z_scores.items()
            ):

                if (
                    pd.notna(z_score)
                    and abs(z_score) > 3
                ):

                    outlier_rows.append(
                        {
                            "company_id":
                                sector_df.loc[
                                    idx,
                                    "company_id",
                                ],

                            "company_name":
                                sector_df.loc[
                                    idx,
                                    "company_name",
                                ],

                            "broad_sector":
                                sector,

                            "metric":
                                kpi,

                            "value":
                                sector_df.loc[
                                    idx,
                                    kpi,
                                ],

                            "sector_mean":
                                mean,

                            "sector_std":
                                std,

                            "z_score":
                                z_score,

                            "absolute_z_score":
                                abs(z_score),

                            "outlier_flag":
                                True,
                        }
                    )

    columns = [
        "company_id",
        "company_name",
        "broad_sector",
        "metric",
        "value",
        "sector_mean",
        "sector_std",
        "z_score",
        "absolute_z_score",
        "outlier_flag",
    ]

    report = pd.DataFrame(
        outlier_rows,
        columns=columns,
    )

    if not report.empty:

        report = (
            report
            .sort_values(
                "absolute_z_score",
                ascending=False,
            )
            .reset_index(drop=True)
        )

    report.to_csv(
        OUTLIER_REPORT_PATH,
        index=False,
    )

    logger.info(
        "Outlier report saved: %s",
        OUTLIER_REPORT_PATH,
    )

    logger.info(
        "Sector-relative outlier flags: %d",
        len(report),
    )

    if report.empty:

        logger.info(
            "No companies exceeded |Z| > 3."
        )

    else:

        logger.info(
            "Unique companies flagged: %d",
            report[
                "company_id"
            ].nunique(),
        )

    return report


# =====================================================================
# PORTFOLIO STATISTICS
# =====================================================================

def generate_portfolio_stats(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Calculate P10, P25, P50, P75, P90, Mean and Std
    for every Day 37 KPI.
    """

    logger.info(
        "Generating portfolio statistics..."
    )

    rows = []

    for kpi in CORRELATION_KPIS:

        values = (
            pd.to_numeric(
                df[kpi],
                errors="coerce",
            )
            .dropna()
        )

        if values.empty:

            raise ValueError(
                f"No numeric observations "
                f"for KPI: {kpi}"
            )

        rows.append(
            {
                "kpi": kpi,

                "p10":
                    values.quantile(
                        0.10
                    ),

                "p25":
                    values.quantile(
                        0.25
                    ),

                "p50":
                    values.quantile(
                        0.50
                    ),

                "p75":
                    values.quantile(
                        0.75
                    ),

                "p90":
                    values.quantile(
                        0.90
                    ),

                "mean":
                    values.mean(),

                "std":
                    values.std(
                        ddof=1
                    ),

                "observations":
                    len(values),
            }
        )

    stats = pd.DataFrame(
        rows
    )

    stats.to_csv(
        PORTFOLIO_STATS_PATH,
        index=False,
    )

    logger.info(
        "Portfolio statistics saved: %s",
        PORTFOLIO_STATS_PATH,
    )

    return stats


# =====================================================================
# VALIDATION
# =====================================================================

def validate_outputs(
    df: pd.DataFrame,
    profile: pd.DataFrame,
    outliers: pd.DataFrame,
    portfolio_stats: pd.DataFrame,
) -> None:
    """Validate all Day 37 outputs."""

    logger.info(
        "Validating Day 37 outputs..."
    )

    # -------------------------------------------------------------
    # Master universe
    # -------------------------------------------------------------

    assert len(df) == EXPECTED_COMPANIES

    assert (
        df["company_id"].nunique()
        == EXPECTED_COMPANIES
    )

    # -------------------------------------------------------------
    # Five clusters
    # -------------------------------------------------------------

    cluster_ids = sorted(
        df["cluster_id"]
        .astype(int)
        .unique()
        .tolist()
    )

    assert cluster_ids == [
        0,
        1,
        2,
        3,
        4,
    ]

    assert len(profile) == 5

    # -------------------------------------------------------------
    # Cluster profile columns
    # -------------------------------------------------------------

    for feature in CLUSTER_FEATURES:

        assert (
            f"{feature}_mean"
            in profile.columns
        )

        assert (
            f"{feature}_median"
            in profile.columns
        )

    # -------------------------------------------------------------
    # Correlation heatmap
    # -------------------------------------------------------------

    assert (
        CORRELATION_HEATMAP_PATH.exists()
    )

    assert (
        CORRELATION_HEATMAP_PATH.stat().st_size
        > 0
    )

    # -------------------------------------------------------------
    # Outlier report
    # -------------------------------------------------------------

    expected_outlier_columns = {
        "company_id",
        "company_name",
        "broad_sector",
        "metric",
        "value",
        "sector_mean",
        "sector_std",
        "z_score",
        "absolute_z_score",
        "outlier_flag",
    }

    assert set(
        outliers.columns
    ) == expected_outlier_columns

    if not outliers.empty:

        assert (
            outliers[
                "absolute_z_score"
            ]
            > 3
        ).all()

        assert (
            outliers[
                "outlier_flag"
            ]
            == True
        ).all()

    # -------------------------------------------------------------
    # Portfolio statistics
    # -------------------------------------------------------------

    assert (
        len(portfolio_stats)
        == len(CORRELATION_KPIS)
    )

    expected_stats_columns = {
        "kpi",
        "p10",
        "p25",
        "p50",
        "p75",
        "p90",
        "mean",
        "std",
        "observations",
    }

    assert set(
        portfolio_stats.columns
    ) == expected_stats_columns

    assert (
        portfolio_stats[
            "observations"
        ]
        .gt(0)
        .all()
    )

    # -------------------------------------------------------------
    # Required files
    # -------------------------------------------------------------

    assert (
        CLUSTER_PROFILE_PATH.exists()
    )

    assert (
        OUTLIER_REPORT_PATH.exists()
    )

    assert (
        PORTFOLIO_STATS_PATH.exists()
    )

    logger.info(
        "Day 37 output validation PASSED"
    )


# =====================================================================
# MAIN
# =====================================================================

def main() -> None:

    logger.info(
        "Starting Day 37 Cluster Profiling & Statistics"
    )

    ensure_directories()

    # -------------------------------------------------------------
    # Build master dataset.
    # -------------------------------------------------------------

    df = build_master_dataset()

    # -------------------------------------------------------------
    # 1. Cluster profiling.
    # -------------------------------------------------------------

    profile = (
        generate_cluster_profile(
            df
        )
    )

    # -------------------------------------------------------------
    # 2. Cluster membership/name review.
    # -------------------------------------------------------------

    review_cluster_members(
        df
    )

    # -------------------------------------------------------------
    # 3. Correlation heatmap.
    # -------------------------------------------------------------

    generate_correlation_heatmap(
        df
    )

    # -------------------------------------------------------------
    # 4. Sector-relative outliers.
    # -------------------------------------------------------------

    outliers = (
        generate_outlier_report(
            df
        )
    )

    # -------------------------------------------------------------
    # 5. Portfolio statistics.
    # -------------------------------------------------------------

    portfolio_stats = (
        generate_portfolio_stats(
            df
        )
    )

    # -------------------------------------------------------------
    # Final validation.
    # -------------------------------------------------------------

    validate_outputs(
        df,
        profile,
        outliers,
        portfolio_stats,
    )

    logger.info(
        "Day 37 Cluster Profiling & Statistics COMPLETE"
    )


if __name__ == "__main__":
    main()