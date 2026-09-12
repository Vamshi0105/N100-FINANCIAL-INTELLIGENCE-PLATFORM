"""
Day 36 — KMeans Clustering

N100 Financial Intelligence Platform

Clusters all 92 companies into five labelled financial
archetypes using:

    1. return_on_equity_pct
    2. debt_to_equity
    3. revenue_cagr_5yr
    4. fcf_cagr_5yr
    5. operating_profit_margin_pct

Processing:

    1. Load all 92 companies from companies table.
    2. Load latest AVAILABLE annual financial-ratio record
       for EACH company.
    3. Load FCF CAGR from cashflow intelligence output.
    4. Join sector information.
    5. Impute missing feature values using sector median.
    6. Fall back to universe median where necessary.
    7. StandardScaler normalization.
    8. KMeans with n_clusters=5 and random_state=42.
    9. Generate elbow plot for k=2..10.
   10. Assign business archetype names.
   11. Calculate distance from assigned centroid.
   12. Validate all 92 companies.
   13. Save output/cluster_labels.csv.
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DB_PATH = (
    PROJECT_ROOT
    / "data"
    / "nifty100.db"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "output"
)

REPORTS_DIR = (
    PROJECT_ROOT
    / "reports"
)

FCF_PATH = (
    OUTPUT_DIR
    / "cashflow_intelligence.xlsx"
)

CLUSTER_OUTPUT_PATH = (
    OUTPUT_DIR
    / "cluster_labels.csv"
)

ELBOW_OUTPUT_PATH = (
    REPORTS_DIR
    / "elbow_plot.png"
)


# ============================================================
# CONFIGURATION
# ============================================================

FEATURES = [
    "return_on_equity_pct",
    "debt_to_equity",
    "revenue_cagr_5yr",
    "fcf_cagr_5yr",
    "operating_profit_margin_pct",
]

N_CLUSTERS = 5

RANDOM_STATE = 42

EXPECTED_COMPANIES = 92


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


# ============================================================
# COMPANY UNIVERSE
# ============================================================

def load_company_universe() -> pd.DataFrame:
    """
    Load the official 92-company universe from companies table.

    This is the authoritative company list.

    Returns:
        DataFrame with company_id.
    """

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    query = """
        SELECT
            id AS company_id
        FROM companies
    """

    with sqlite3.connect(DB_PATH) as connection:

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

    df = df.drop_duplicates(
        subset=["company_id"]
    ).reset_index(
        drop=True
    )

    logger.info(
        "Official company universe: %d",
        len(df),
    )

    if len(df) != EXPECTED_COMPANIES:

        raise ValueError(
            "Expected "
            f"{EXPECTED_COMPANIES} companies in companies table, "
            f"found {len(df)}"
        )

    return df


# ============================================================
# FINANCIAL RATIO DATA
# ============================================================

def load_financial_data() -> pd.DataFrame:
    """
    Load the latest AVAILABLE annual financial-ratio record
    for each company.

    IMPORTANT:

    We do NOT use:

        WHERE year = MAX(year)

    because that would only return companies having a row
    in the single globally latest year.

    Instead, we load all annual records and select the latest
    available annual record separately for every company.
    """

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    query = """
        SELECT
            CAST(company_id AS TEXT) AS company_id,
            year,
            return_on_equity_pct,
            debt_to_equity,
            revenue_cagr_5yr,
            operating_profit_margin_pct
        FROM financial_ratios
    """

    with sqlite3.connect(DB_PATH) as connection:

        df = pd.read_sql_query(
            query,
            connection,
        )

    if df.empty:

        raise ValueError(
            "financial_ratios returned no rows"
        )

    df["company_id"] = (
        df["company_id"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    # --------------------------------------------------------
    # Normalize year
    # --------------------------------------------------------

    df["year_text"] = (
        df["year"]
        .astype(str)
        .str.strip()
    )

    df["year_numeric"] = pd.to_numeric(
        df["year_text"]
        .str.extract(r"(\d{4})")[0],
        errors="coerce",
    )

    # --------------------------------------------------------
    # Prefer annual March records.
    #
    # Existing project convention uses YYYY-03 for annual
    # reporting periods.
    # --------------------------------------------------------

    annual_df = df[
        df["year_text"].str.endswith("-03")
    ].copy()

    # Defensive fallback.
    #
    # If the database does not contain YYYY-03 records,
    # use all records rather than returning an empty dataset.
    if annual_df.empty:

        logger.warning(
            "No YYYY-03 annual records found. "
            "Falling back to all financial-ratio records."
        )

        annual_df = df.copy()

    # --------------------------------------------------------
    # Latest available year PER COMPANY
    # --------------------------------------------------------

    annual_df = annual_df.sort_values(
        [
            "company_id",
            "year_numeric",
        ]
    )

    latest = (
        annual_df
        .groupby(
            "company_id",
            as_index=False,
        )
        .tail(1)
        .copy()
    )

    latest = latest.drop(
        columns=[
            "year_text",
            "year_numeric",
        ],
        errors="ignore",
    )

    latest = latest.reset_index(
        drop=True
    )

    logger.info(
        "Financial-ratio companies available: %d",
        df["company_id"].nunique(),
    )

    logger.info(
        "Latest annual company records retained: %d",
        len(latest),
    )

    return latest


# ============================================================
# SECTOR DATA
# ============================================================

def load_sector_data() -> pd.DataFrame:
    """
    Load broad-sector assignments.

    Sector information is required because missing clustering
    metrics must be imputed using sector medians.
    """

    query = """
        SELECT
            CAST(company_id AS TEXT) AS company_id,
            broad_sector
        FROM sectors
    """

    with sqlite3.connect(DB_PATH) as connection:

        df = pd.read_sql_query(
            query,
            connection,
        )

    if df.empty:

        raise ValueError(
            "sectors table returned no rows"
        )

    df["company_id"] = (
        df["company_id"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    df["broad_sector"] = (
        df["broad_sector"]
        .astype(str)
        .str.strip()
    )

    df = df.drop_duplicates(
        subset=["company_id"],
        keep="first",
    )

    logger.info(
        "Sector assignments loaded: %d",
        len(df),
    )

    return df


# ============================================================
# FCF CAGR DATA
# ============================================================

def load_fcf_data() -> pd.DataFrame:
    """
    Load 5-year FCF CAGR.

    The Day 31 cash-flow intelligence module produces
    fcf_cagr_5yr in:

        output/cashflow_intelligence.xlsx
    """

    if not FCF_PATH.exists():

        raise FileNotFoundError(
            "Cash-flow intelligence output not found: "
            f"{FCF_PATH}"
        )

    df = pd.read_excel(
        FCF_PATH
    )

    required_columns = {
        "company_id",
        "fcf_cagr_5yr",
    }

    missing_columns = (
        required_columns
        - set(df.columns)
    )

    if missing_columns:

        raise ValueError(
            "cashflow_intelligence.xlsx is missing columns: "
            + ", ".join(
                sorted(missing_columns)
            )
        )

    df["company_id"] = (
        df["company_id"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    df["fcf_cagr_5yr"] = pd.to_numeric(
        df["fcf_cagr_5yr"],
        errors="coerce",
    )

    df = df[
        [
            "company_id",
            "fcf_cagr_5yr",
        ]
    ].drop_duplicates(
        subset=["company_id"],
        keep="first",
    )

    logger.info(
        "FCF CAGR companies loaded: %d",
        df["company_id"].nunique(),
    )

    return df


# ============================================================
# PREPARE CLUSTERING DATA
# ============================================================

def prepare_clustering_data() -> pd.DataFrame:
    """
    Build the complete 92-company clustering dataset.

    The companies table is treated as the authoritative
    universe.

    Financial data, FCF CAGR and sector data are left-joined
    onto that universe so missing metrics can be handled by
    the required imputation process.
    """

    universe = load_company_universe()

    financial = load_financial_data()

    sectors = load_sector_data()

    fcf = load_fcf_data()

    # --------------------------------------------------------
    # Start with all 92 official companies.
    # --------------------------------------------------------

    df = universe.merge(
        financial,
        on="company_id",
        how="left",
    )

    df = df.merge(
        sectors,
        on="company_id",
        how="left",
    )

    df = df.merge(
        fcf,
        on="company_id",
        how="left",
    )

    # --------------------------------------------------------
    # Check company coverage.
    # --------------------------------------------------------

    logger.info(
        "Companies after financial-data join: %d",
        df["company_id"].nunique(),
    )

    if len(df) != EXPECTED_COMPANIES:

        raise ValueError(
            "Expected "
            f"{EXPECTED_COMPANIES} companies after joins, "
            f"found {len(df)}"
        )

    # --------------------------------------------------------
    # Sector coverage.
    # --------------------------------------------------------

    missing_sector = (
        df["broad_sector"]
        .isna()
        .sum()
    )

    if missing_sector:

        missing_ids = (
            df.loc[
                df["broad_sector"].isna(),
                "company_id",
            ]
            .tolist()
        )

        raise ValueError(
            f"{missing_sector} companies have no sector "
            "assignment: "
            + ", ".join(missing_ids)
        )

    # --------------------------------------------------------
    # Numeric conversion.
    # --------------------------------------------------------

    for feature in FEATURES:

        df[feature] = pd.to_numeric(
            df[feature],
            errors="coerce",
        )

    # --------------------------------------------------------
    # Required feature columns.
    # --------------------------------------------------------

    missing_features = [
        feature
        for feature in FEATURES
        if feature not in df.columns
    ]

    if missing_features:

        raise ValueError(
            "Missing clustering features: "
            + ", ".join(missing_features)
        )

    logger.info(
        "Prepared complete clustering universe: %d companies",
        len(df),
    )

    return df


# ============================================================
# SECTOR MEDIAN IMPUTATION
# ============================================================

def impute_sector_medians(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Impute missing values using the median of the company's
    broad sector.

    If an entire sector is missing a particular feature,
    fall back to the overall universe median for that feature.
    """

    result = df.copy()

    logger.info(
        "Missing values BEFORE sector imputation:"
    )

    before = (
        result[FEATURES]
        .isna()
        .sum()
    )

    for feature, count in before.items():

        logger.info(
            "  %s: %d",
            feature,
            count,
        )

    # --------------------------------------------------------
    # Sector median imputation.
    # --------------------------------------------------------

    for feature in FEATURES:

        sector_median = (
            result
            .groupby("broad_sector")[feature]
            .transform("median")
        )

        result[feature] = (
            result[feature]
            .fillna(sector_median)
        )

        # ----------------------------------------------------
        # Universe median fallback.
        # ----------------------------------------------------

        global_median = (
            result[feature]
            .median()
        )

        if pd.isna(global_median):

            raise ValueError(
                "Cannot impute feature because both sector "
                f"and universe medians are unavailable: "
                f"{feature}"
            )

        result[feature] = (
            result[feature]
            .fillna(global_median)
        )

    # --------------------------------------------------------
    # Final NaN check.
    # --------------------------------------------------------

    after = (
        result[FEATURES]
        .isna()
        .sum()
    )

    logger.info(
        "Missing values AFTER sector imputation:"
    )

    for feature, count in after.items():

        logger.info(
            "  %s: %d",
            feature,
            count,
        )

    if (
        result[FEATURES]
        .isna()
        .any()
        .any()
    ):

        raise ValueError(
            "NaN values remain after imputation"
        )

    logger.info(
        "Sector-median imputation PASSED"
    )

    return result


# ============================================================
# STANDARD SCALING
# ============================================================

def scale_features(
    df: pd.DataFrame,
) -> tuple[StandardScaler, object]:
    """
    Apply StandardScaler.

    Resulting features have approximately:
        mean = 0
        standard deviation = 1
    """

    scaler = StandardScaler()

    X_scaled = scaler.fit_transform(
        df[FEATURES]
    )

    logger.info(
        "StandardScaler applied to %d features",
        len(FEATURES),
    )

    return scaler, X_scaled


# ============================================================
# ELBOW PLOT
# ============================================================

def generate_elbow_plot(
    X_scaled,
) -> list[float]:
    """
    Calculate KMeans inertia for k=2 through k=10.

    Save:
        reports/elbow_plot.png
    """

    k_values = list(
        range(2, 11)
    )

    inertias = []

    logger.info(
        "Generating elbow plot..."
    )

    for k in k_values:

        model = KMeans(
            n_clusters=k,
            random_state=RANDOM_STATE,
            n_init=10,
        )

        model.fit(
            X_scaled
        )

        inertia = (
            model.inertia_
        )

        inertias.append(
            inertia
        )

        logger.info(
            "Elbow k=%d inertia=%.4f",
            k,
            inertia,
        )

    REPORTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    plt.figure(
        figsize=(8, 5)
    )

    plt.plot(
        k_values,
        inertias,
        marker="o",
    )

    plt.xlabel(
        "Number of clusters (k)"
    )

    plt.ylabel(
        "Inertia"
    )

    plt.title(
        "KMeans Elbow Plot"
    )

    plt.xticks(
        k_values
    )

    plt.grid(
        True,
        alpha=0.3,
    )

    plt.tight_layout()

    plt.savefig(
        ELBOW_OUTPUT_PATH,
        dpi=150,
        bbox_inches="tight",
    )

    plt.close()

    logger.info(
        "Elbow plot saved: %s",
        ELBOW_OUTPUT_PATH,
    )

    return inertias


# ============================================================
# ARCHETYPE LABELING
# ============================================================

def assign_archetype_names(
    model: KMeans,
    scaler: StandardScaler,
) -> dict[int, str]:
    """
    Convert arbitrary KMeans cluster IDs into deterministic
    business archetype labels.

    Required labels:

        High-Quality Growth
        Defensive Dividend
        Value Cyclicals
        Distressed
        Emerging Growth
    """

    centroids_scaled = (
        model.cluster_centers_
    )

    centroids = (
        scaler.inverse_transform(
            centroids_scaled
        )
    )

    centroid_df = pd.DataFrame(
        centroids,
        columns=FEATURES,
    )

    # --------------------------------------------------------
    # Percentile ranks across centroids.
    # --------------------------------------------------------

    ranks = (
        centroid_df.rank(
            pct=True
        )
    )

    # --------------------------------------------------------
    # DISTRESSED
    #
    # Weak profitability/growth and relatively high leverage.
    # --------------------------------------------------------

    distressed_score = (
        (1 - ranks["return_on_equity_pct"])
        + ranks["debt_to_equity"]
        + (1 - ranks["revenue_cagr_5yr"])
        + (1 - ranks["fcf_cagr_5yr"])
        + (1 - ranks["operating_profit_margin_pct"])
    )

    distressed_cluster = int(
        distressed_score.idxmax()
    )

    labels = {
        distressed_cluster: "Distressed"
    }

    remaining = [
        cluster_id
        for cluster_id in range(N_CLUSTERS)
        if cluster_id not in labels
    ]

    # --------------------------------------------------------
    # HIGH-QUALITY GROWTH
    #
    # Strong ROE, margins, revenue growth and FCF growth
    # combined with controlled leverage.
    # --------------------------------------------------------

    quality_score = (
        ranks["return_on_equity_pct"]
        + (1 - ranks["debt_to_equity"])
        + ranks["revenue_cagr_5yr"]
        + ranks["fcf_cagr_5yr"]
        + ranks["operating_profit_margin_pct"]
    )

    quality_cluster = max(
        remaining,
        key=lambda cluster_id:
            quality_score.iloc[cluster_id],
    )

    labels[
        quality_cluster
    ] = "High-Quality Growth"

    remaining.remove(
        quality_cluster
    )

    # --------------------------------------------------------
    # EMERGING GROWTH
    #
    # Strong revenue/FCF growth among the remaining clusters.
    # --------------------------------------------------------

    emerging_growth_score = (
        ranks["revenue_cagr_5yr"]
        + ranks["fcf_cagr_5yr"]
        + (1 - ranks["debt_to_equity"])
    )

    emerging_cluster = max(
        remaining,
        key=lambda cluster_id:
            emerging_growth_score.iloc[
                cluster_id
            ],
    )

    labels[
        emerging_cluster
    ] = "Emerging Growth"

    remaining.remove(
        emerging_cluster
    )

    # --------------------------------------------------------
    # DEFENSIVE DIVIDEND
    #
    # Lower leverage + stronger profitability + comparatively
    # lower growth.
    # --------------------------------------------------------

    defensive_score = (
        ranks["return_on_equity_pct"]
        + (1 - ranks["debt_to_equity"])
        + ranks["operating_profit_margin_pct"]
        + (1 - ranks["revenue_cagr_5yr"])
    )

    defensive_cluster = max(
        remaining,
        key=lambda cluster_id:
            defensive_score.iloc[
                cluster_id
            ],
    )

    labels[
        defensive_cluster
    ] = "Defensive Dividend"

    remaining.remove(
        defensive_cluster
    )

    # --------------------------------------------------------
    # VALUE CYCLICALS
    #
    # The final remaining cluster.
    # --------------------------------------------------------

    if len(remaining) != 1:

        raise RuntimeError(
            "Unable to assign unique archetype labels"
        )

    labels[
        remaining[0]
    ] = "Value Cyclicals"

    logger.info(
        "Cluster archetype mapping:"
    )

    for cluster_id in sorted(labels):

        logger.info(
            "  Cluster %d -> %s",
            cluster_id,
            labels[cluster_id],
        )

    return labels


# ============================================================
# RUN KMEANS
# ============================================================

def run_clustering(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Execute complete clustering workflow.
    """

    scaler, X_scaled = (
        scale_features(
            df
        )
    )

    # --------------------------------------------------------
    # Elbow analysis
    # --------------------------------------------------------

    generate_elbow_plot(
        X_scaled
    )

    # --------------------------------------------------------
    # Five-cluster KMeans
    # --------------------------------------------------------

    logger.info(
        "Running KMeans with n_clusters=%d, random_state=%d",
        N_CLUSTERS,
        RANDOM_STATE,
    )

    model = KMeans(
        n_clusters=N_CLUSTERS,
        random_state=RANDOM_STATE,
        n_init=10,
    )

    cluster_ids = (
        model.fit_predict(
            X_scaled
        )
    )

    # --------------------------------------------------------
    # Distance from every point to every centroid.
    # --------------------------------------------------------

    distances = (
        model.transform(
            X_scaled
        )
    )

    # Distance to the company's assigned centroid.
    assigned_distances = (
        distances[
            range(len(df)),
            cluster_ids,
        ]
    )

    # --------------------------------------------------------
    # Business archetype names.
    # --------------------------------------------------------

    cluster_names = (
        assign_archetype_names(
            model,
            scaler,
        )
    )

    # --------------------------------------------------------
    # Output.
    # --------------------------------------------------------

    result = df[
        ["company_id"]
    ].copy()

    result["cluster_id"] = (
        cluster_ids
    )

    result["cluster_name"] = [
        cluster_names[
            int(cluster_id)
        ]
        for cluster_id in cluster_ids
    ]

    result[
        "distance_from_centroid"
    ] = (
        pd.Series(
            assigned_distances
        )
        .round(6)
    )

    result = (
        result
        .sort_values(
            [
                "cluster_id",
                "company_id",
            ]
        )
        .reset_index(
            drop=True
        )
    )

    return result


# ============================================================
# VALIDATION
# ============================================================

def validate_clusters(
    result: pd.DataFrame,
) -> None:
    """
    Validate all Day 36 cluster acceptance requirements.
    """

    logger.info(
        "Validating cluster output..."
    )

    # --------------------------------------------------------
    # Row count
    # --------------------------------------------------------

    if len(result) != EXPECTED_COMPANIES:

        raise AssertionError(
            f"Expected {EXPECTED_COMPANIES} rows, "
            f"found {len(result)}"
        )

    # --------------------------------------------------------
    # Unique companies
    # --------------------------------------------------------

    unique_companies = (
        result["company_id"]
        .nunique()
    )

    if unique_companies != EXPECTED_COMPANIES:

        raise AssertionError(
            "Expected "
            f"{EXPECTED_COMPANIES} unique companies, "
            f"found {unique_companies}"
        )

    # --------------------------------------------------------
    # Required columns
    # --------------------------------------------------------

    required_columns = [
        "company_id",
        "cluster_id",
        "cluster_name",
        "distance_from_centroid",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in result.columns
    ]

    if missing_columns:

        raise AssertionError(
            "Missing output columns: "
            + ", ".join(missing_columns)
        )

    # --------------------------------------------------------
    # Cluster ID validation
    # --------------------------------------------------------

    if result["cluster_id"].isna().any():

        raise AssertionError(
            "Null cluster_id detected"
        )

    if not result["cluster_id"].between(
        0,
        4,
    ).all():

        raise AssertionError(
            "Cluster IDs must be between 0 and 4"
        )

    # --------------------------------------------------------
    # Every cluster should actually exist.
    # --------------------------------------------------------

    cluster_count = (
        result["cluster_id"]
        .nunique()
    )

    if cluster_count != N_CLUSTERS:

        raise AssertionError(
            f"Expected {N_CLUSTERS} clusters, "
            f"found {cluster_count}"
        )

    # --------------------------------------------------------
    # Cluster names
    # --------------------------------------------------------

    expected_names = {
        "High-Quality Growth",
        "Defensive Dividend",
        "Value Cyclicals",
        "Distressed",
        "Emerging Growth",
    }

    actual_names = set(
        result["cluster_name"]
        .dropna()
        .unique()
    )

    if actual_names != expected_names:

        raise AssertionError(
            "Unexpected cluster names.\n"
            f"Expected: {sorted(expected_names)}\n"
            f"Actual: {sorted(actual_names)}"
        )

    # --------------------------------------------------------
    # Distance validation
    # --------------------------------------------------------

    if (
        result["distance_from_centroid"]
        .isna()
        .any()
    ):

        raise AssertionError(
            "Null distance_from_centroid detected"
        )

    if (
        result["distance_from_centroid"]
        < 0
    ).any():

        raise AssertionError(
            "Negative centroid distance detected"
        )

    # --------------------------------------------------------
    # Distribution
    # --------------------------------------------------------

    distribution = (
        result[
            [
                "cluster_id",
                "cluster_name",
            ]
        ]
        .value_counts()
        .sort_index()
    )

    logger.info(
        "Cluster distribution:"
    )

    for (
        cluster_id,
        cluster_name,
    ), count in distribution.items():

        logger.info(
            "  Cluster %d | %-22s | %d companies",
            cluster_id,
            cluster_name,
            count,
        )

    logger.info(
        "Cluster validation PASSED: %d/%d companies assigned",
        unique_companies,
        EXPECTED_COMPANIES,
    )


# ============================================================
# SAVE OUTPUT
# ============================================================

def save_output(
    result: pd.DataFrame,
) -> None:
    """
    Save cluster_labels.csv.
    """

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output = result[
        [
            "company_id",
            "cluster_id",
            "cluster_name",
            "distance_from_centroid",
        ]
    ].copy()

    output.to_csv(
        CLUSTER_OUTPUT_PATH,
        index=False,
    )

    logger.info(
        "Cluster labels saved: %s",
        CLUSTER_OUTPUT_PATH,
    )


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    """
    Execute Day 36.
    """

    logger.info(
        "Starting Day 36 KMeans Clustering"
    )

    # --------------------------------------------------------
    # 1. Prepare data
    # --------------------------------------------------------

    df = (
        prepare_clustering_data()
    )

    # --------------------------------------------------------
    # 2. Sector median imputation
    # --------------------------------------------------------

    df = (
        impute_sector_medians(
            df
        )
    )

    # --------------------------------------------------------
    # 3. KMeans
    # --------------------------------------------------------

    result = (
        run_clustering(
            df
        )
    )

    # --------------------------------------------------------
    # 4. Validate
    # --------------------------------------------------------

    validate_clusters(
        result
    )

    # --------------------------------------------------------
    # 5. Save
    # --------------------------------------------------------

    save_output(
        result
    )

    logger.info(
        "Day 36 KMeans Clustering COMPLETE"
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()