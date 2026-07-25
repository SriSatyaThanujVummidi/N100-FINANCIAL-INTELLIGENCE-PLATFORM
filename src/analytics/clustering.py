"""
Day 36 -- KMeans Clustering (Sprint 6, Module 10)

Clusters all 92 companies into 5 archetypes based on 5 financial features:
    - return_on_equity_pct
    - debt_to_equity
    - revenue_cagr_5yr   (computed on the fly -- not persisted in financial_ratios, per Sprint 3 Day 15 finding)
    - fcf_cagr_5yr       (computed on the fly -- FCF = CFO + CFI, same definition as Day 11/31)
    - operating_profit_margin_pct

See PROGRESS.md Day 36 entry for the judgment calls behind the masking/imputation/
CAGR design choices below.
"""

import logging
import os
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DB_PATH = os.environ.get("DB_PATH", "data/nifty100.db")
OUTPUT_DIR = Path("output")
REPORTS_DIR = Path("reports")

ROE_SANITY_BOUND = 500.0  # +/-500%, same bound as Day 13's edge_cases.py
FCF_CAGR_SANITY_BOUND = (
    100.0  # NEW, derived from the real distribution (not guessed): CIPLA
)
# is 228.75%, the next-highest is INDIGO at 71.57% -- a 157-point
# gap, vs. ~13 points anywhere else in the sorted list. 100 sits
# in that gap and catches only CIPLA. revenue_cagr_5yr is NOT
# bounded -- its real distribution (max TRENT 36.3%, min DLF
# -5.1%) has no comparable outlier, so no cap is justified there.

FEATURE_COLS = [
    "return_on_equity_pct",
    "debt_to_equity",
    "revenue_cagr_5yr",
    "fcf_cagr_5yr",
    "operating_profit_margin_pct",
]


def get_connection() -> sqlite3.Connection:
    """Open a connection to nifty100.db with FK enforcement on."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def load_latest_ratios(conn: sqlite3.Connection) -> pd.DataFrame:
    """Load each company's own latest-year ROE/D-E/OPM (per-company MAX(year), not a global filter --
    a global year filter would silently drop Sept/Dec fiscal-year-end companies, per Day 15's finding).
    """
    query = """
        SELECT fr.company_id,
               fr.return_on_equity_pct,
               fr.debt_to_equity,
               fr.operating_profit_margin_pct
        FROM financial_ratios fr
        INNER JOIN (
            SELECT company_id, MAX(year) AS max_year
            FROM financial_ratios
            GROUP BY company_id
        ) latest
          ON fr.company_id = latest.company_id
         AND fr.year = latest.max_year
    """
    return pd.read_sql_query(query, conn)


def load_sectors(conn: sqlite3.Connection) -> pd.DataFrame:
    """Load broad_sector mapping used for sector-median imputation."""
    return pd.read_sql_query("SELECT company_id, broad_sector FROM sectors", conn)


def compute_cagr(start, end, years: int):
    """Spec Section 23.1 decision table. Returns None for ZERO_BASE / DECLINE_TO_LOSS /
    TURNAROUND / BOTH_NEGATIVE -- only a positive-to-positive base/end computes a real value.
    """
    if start is None or end is None or pd.isna(start) or pd.isna(end):
        return None
    if start == 0:
        return None
    if start > 0 and end > 0:
        return ((end / start) ** (1 / years) - 1) * 100
    return None  # covers decline-to-loss, turnaround, both-negative


def five_year_cagr_by_company(df: pd.DataFrame, value_col: str) -> pd.Series:
    """
    df must have columns: company_id, year, <value_col>.
    Uses each company's own 6th-most-recent reported row as the CAGR base (index-based
    5-year gap), not calendar arithmetic -- required for Sept/Dec fiscal year-end companies.
    Companies with fewer than 6 reported years return None (insufficient history).
    """
    results = {}
    for company_id, grp in df.groupby("company_id"):
        grp = grp.sort_values("year")
        values = grp[value_col].tolist()
        if len(values) < 6:
            results[company_id] = None
            continue
        start, end = values[-6], values[-1]
        results[company_id] = compute_cagr(start, end, years=5)
    return pd.Series(results, name=value_col + "_5yr")


def load_revenue_cagr(conn: sqlite3.Connection) -> pd.DataFrame:
    """Returns a DataFrame with company_id as a column (not an index) so it merges cleanly."""
    df = pd.read_sql_query("SELECT company_id, year, sales FROM profitandloss", conn)
    s = five_year_cagr_by_company(df, "sales").rename("revenue_cagr_5yr")
    return s.rename_axis("company_id").reset_index()


def load_fcf_cagr(conn: sqlite3.Connection) -> pd.DataFrame:
    """Returns a DataFrame with company_id as a column (not an index) so it merges cleanly."""
    df = pd.read_sql_query(
        "SELECT company_id, year, operating_activity, investing_activity FROM cashflow",
        conn,
    )
    df["fcf"] = df["operating_activity"] + df["investing_activity"]
    s = five_year_cagr_by_company(df, "fcf").rename("fcf_cagr_5yr")
    return s.rename_axis("company_id").reset_index()


def apply_sanity_bound(df: pd.DataFrame, column: str, bound: float) -> pd.DataFrame:
    """Mask |value| > bound to NaN before imputation. Generic version of Day 13's ROE/ROCE
    sanity-bound pattern -- used for return_on_equity_pct (bound=500) and fcf_cagr_5yr
    (bound=100, derived from the real distribution -- see FCF_CAGR_SANITY_BOUND note above).
    """
    mask = df[column].abs() > bound
    n_flagged = int(mask.sum())
    if n_flagged:
        flagged_ids = df.loc[mask, "company_id"].tolist()
        logger.warning(
            "%s sanity-bound masked for %d companies (|value| > %.0f): %s",
            column,
            n_flagged,
            bound,
            flagged_ids,
        )
    df.loc[mask, column] = np.nan
    return df


def impute_by_sector_median(df: pd.DataFrame, feature_cols: list) -> pd.DataFrame:
    """Missing values (true gaps + sanity-masked) filled with sector median; global median as
    a defensive fallback if an entire sector is missing a feature."""
    for col in feature_cols:
        n_missing_before = int(df[col].isna().sum())
        df[col] = df.groupby("broad_sector")[col].transform(
            lambda s: s.fillna(s.median())
        )
        df[col] = df[col].fillna(df[col].median())
        n_missing_after = int(df[col].isna().sum())
        if n_missing_before:
            logger.info(
                "%s: %d values imputed by sector median (%d still missing after global fallback)",
                col,
                n_missing_before,
                n_missing_after,
            )
    return df


def build_feature_table(conn: sqlite3.Connection) -> pd.DataFrame:
    """Build feature table."""
    ratios = load_latest_ratios(conn)
    sectors = load_sectors(conn)
    revenue_cagr = load_revenue_cagr(conn)
    fcf_cagr = load_fcf_cagr(conn)

    df = ratios.merge(sectors, on="company_id", how="left")
    df = df.merge(revenue_cagr, on="company_id", how="left")
    df = df.merge(fcf_cagr, on="company_id", how="left")

    missing_sector = int(df["broad_sector"].isna().sum())
    if missing_sector:
        logger.warning(
            "%d companies have no sector mapping -- global median used for their imputation",
            missing_sector,
        )

    df = apply_sanity_bound(df, "return_on_equity_pct", ROE_SANITY_BOUND)
    df = apply_sanity_bound(df, "fcf_cagr_5yr", FCF_CAGR_SANITY_BOUND)
    df = impute_by_sector_median(df, FEATURE_COLS)
    return df


def run_elbow_analysis(X_scaled: np.ndarray) -> None:
    """Inertia vs k=2..10, saved to reports/elbow_plot.png with k=5 marked."""
    inertias = []
    k_range = range(2, 11)
    for k in k_range:
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        km.fit(X_scaled)
        inertias.append(km.inertia_)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(8, 5))
    plt.plot(list(k_range), inertias, marker="o")
    plt.axvline(x=5, color="red", linestyle="--", label="k=5 (chosen)")
    plt.xlabel("Number of clusters (k)")
    plt.ylabel("Inertia")
    plt.title("Elbow Plot -- KMeans Inertia vs k")
    plt.legend()
    plt.tight_layout()
    plt.savefig(REPORTS_DIR / "elbow_plot.png", dpi=150)
    plt.close()
    logger.info("Elbow plot saved to reports/elbow_plot.png")

    print("\nElbow analysis (k=2..10):")
    for k, inertia in zip(k_range, inertias):
        marker = "  <-- chosen k" if k == 5 else ""
        print(f"  k={k:2d}  inertia={inertia:,.1f}{marker}")


def run_kmeans(df: pd.DataFrame) -> pd.DataFrame:
    """Run kmeans."""
    X = df[FEATURE_COLS].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    run_elbow_analysis(X_scaled)

    kmeans = KMeans(n_clusters=5, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X_scaled)
    distances = np.linalg.norm(X_scaled - kmeans.cluster_centers_[labels], axis=1)

    df["cluster_id"] = labels
    df["cluster_name"] = df["cluster_id"].apply(
        lambda c: f"Cluster_{c}"
    )  # placeholder -- named for real on Day 37
    df["distance_from_centroid"] = distances
    return df


def main() -> None:
    """Main."""
    conn = get_connection()
    try:
        df = build_feature_table(conn)
    finally:
        conn.close()

    assert len(df) == 92, f"Expected 92 companies, got {len(df)}"
    for col in FEATURE_COLS:
        n_nan = int(df[col].isna().sum())
        assert n_nan == 0, f"{col} still has {n_nan} NaN after imputation"

    df = run_kmeans(df)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_cols = ["company_id", "cluster_id", "cluster_name", "distance_from_centroid"]
    df[out_cols].sort_values("company_id").to_csv(
        OUTPUT_DIR / "cluster_labels.csv", index=False
    )
    logger.info("output/cluster_labels.csv written -- %d rows", len(df))

    print("\nCluster sizes:")
    print(df["cluster_id"].value_counts().sort_index())

    print("\nCluster feature means (for Day 37 profiling/naming):")
    print(df.groupby("cluster_id")[FEATURE_COLS].mean().round(2))


if __name__ == "__main__":
    main()
