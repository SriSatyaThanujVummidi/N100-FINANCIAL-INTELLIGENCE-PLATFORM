"""
Day 37 -- Correlation Heatmap, Outlier Detection & Portfolio Statistics (Sprint 6, Module 10)

Resolves a "10 core KPI" column set from financial_ratios via schema introspection (PRAGMA
table_info) rather than hardcoding exact column names -- same precedent as Day 31/36.

FIX (post first real run): ROE/ROCE/ROA were NOT sanity-bound masked before this module
computed correlation/outliers/portfolio stats, unlike every other module downstream of
financial_ratios (composite score, screener, peer percentiles -- Day 13/17/18). This produced
the same corruption pattern already documented elsewhere: ROE Mean=123.90/Std=637.14 vs. a sane
Median=16.72, driven by HAL/BEL/INDIGO's known equity-anomaly. Now masked with the same
+/-500% bound before correlation, outlier detection, and percentile stats are computed.

FIX (post second run): HINDALCO's Operating Profit Margin % (88.9%) is NOT caught by the flat
+/-500 bound and can't be -- 80-100% OPM is legitimate for Financials/insurers (ICICIPRULI,
RECLTD, IRFC, HDFCLIFE all sit in that range genuinely). HINDALCO is instead excluded by a
targeted, evidence-based company-specific exclusion (see KNOWN_ANOMALOUS_VALUES below), not a
threshold -- confirmed via two independent cross-checks in day37_diagnose_hindalco.py.
"""

import logging
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

try:
    import seaborn as sns
except ImportError:
    sns = None

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DB_PATH = "data/nifty100.db"
OUTPUT_DIR = Path("output")
REPORTS_DIR = Path("reports")

RATIO_SANITY_BOUND = (
    500.0  # same bound/precedent as Day 13's edge_cases.py and Day 36's clustering.py
)
RATIO_COLUMNS_TO_MASK = [
    "Return on Equity %",
    "Return on Capital Employed %",
    "Return on Assets %",
]

# Company-specific exclusions confirmed via independent cross-validation (NOT a generic bound --
# a flat OPM threshold can't work since 80-100% is legitimate for Financials/insurers).
# HINDALCO: sales-opm_percentage=operating_profit exact match for 5 straight years (source field
# defect) + companies.xlsx's independently-sourced roce_percentage=11.3% (in-band for Materials,
# contradicts the 88.9% P&L-derived OPM). Confirmed Day 37 via day37_diagnose_hindalco.py.
KNOWN_ANOMALOUS_VALUES = {
    ("HINDALCO", "Operating Profit Margin %"),
}

KPI_CANDIDATES = {
    "Net Profit Margin %": ["net_profit_margin_pct"],
    "Operating Profit Margin %": ["operating_profit_margin_pct"],
    "Return on Equity %": ["return_on_equity_pct"],
    "Return on Capital Employed %": ["return_on_capital_employed_pct", "roce_pct"],
    "Return on Assets %": ["return_on_assets_pct"],
    "Debt to Equity": ["debt_to_equity"],
    "Interest Coverage": ["interest_coverage_ratio", "interest_coverage", "icr"],
    "Asset Turnover": ["asset_turnover"],
    "Free Cash Flow (Cr)": ["free_cash_flow_cr", "fcf_cr"],
    "Earnings Per Share": ["earnings_per_share", "eps"],
}


def get_connection() -> sqlite3.Connection:
    """Get connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def resolve_kpi_columns(conn: sqlite3.Connection) -> dict:
    """Resolve kpi columns."""
    cols = {
        row[1] for row in conn.execute("PRAGMA table_info(financial_ratios)").fetchall()
    }
    resolved = {}
    for display_name, candidates in KPI_CANDIDATES.items():
        match = next((c for c in candidates if c in cols), None)
        if match:
            resolved[display_name] = match
        else:
            logger.warning(
                "KPI '%s' -- none of %s found in financial_ratios schema, skipped",
                display_name,
                candidates,
            )
    logger.info(
        "Resolved %d/%d core KPIs: %s",
        len(resolved),
        len(KPI_CANDIDATES),
        list(resolved.values()),
    )
    return resolved


def load_latest_kpis(conn: sqlite3.Connection, kpi_map: dict) -> pd.DataFrame:
    """Load latest kpis."""
    select_cols = ", ".join(f"fr.{col}" for col in kpi_map.values())
    query = f"""
        SELECT fr.company_id, {select_cols}
        FROM financial_ratios fr
        INNER JOIN (
            SELECT company_id, MAX(year) AS max_year
            FROM financial_ratios
            GROUP BY company_id
        ) latest
          ON fr.company_id = latest.company_id
         AND fr.year = latest.max_year
    """
    df = pd.read_sql_query(query, conn)
    sectors = pd.read_sql_query("SELECT company_id, broad_sector FROM sectors", conn)
    df = df.merge(sectors, on="company_id", how="left")
    rename = {v: k for k, v in kpi_map.items()}
    df = df.rename(columns=rename)
    return df


def apply_ratio_sanity_bounds(df: pd.DataFrame) -> pd.DataFrame:
    """Mask |value| > 500 to NaN for ROE/ROCE/ROA -- same bound/precedent as Day 13/17/18/36.
    Not imputed here (unlike clustering.py) -- this module's downstream functions already
    handle NaN via .dropna()/pandas' pairwise-NaN-aware .corr()."""
    for col in RATIO_COLUMNS_TO_MASK:
        if col not in df.columns:
            continue
        mask = df[col].abs() > RATIO_SANITY_BOUND
        n_flagged = int(mask.sum())
        if n_flagged:
            flagged_ids = df.loc[mask, "company_id"].tolist()
            logger.warning(
                "%s sanity-bound masked for %d companies (|value| > %.0f): %s",
                col,
                n_flagged,
                RATIO_SANITY_BOUND,
                flagged_ids,
            )
        df.loc[mask, col] = np.nan
    return df


def apply_known_anomaly_exclusions(df: pd.DataFrame) -> pd.DataFrame:
    """Targeted, evidence-based exclusions for anomalies a flat bound can't catch without
    also catching legitimate values elsewhere (see KNOWN_ANOMALOUS_VALUES docstring above).
    """
    for company_id, col in KNOWN_ANOMALOUS_VALUES:
        if col not in df.columns:
            continue
        mask = df["company_id"] == company_id
        if mask.any():
            logger.warning(
                "%s excluded for %s -- confirmed source-field defect, not a bound",
                company_id,
                col,
            )
            df.loc[mask, col] = np.nan
    return df


def generate_correlation_heatmap(df: pd.DataFrame, kpi_names: list) -> None:
    """Generate correlation heatmap."""
    if sns is None:
        logger.error(
            "seaborn not installed -- run: pip install seaborn --break-system-packages"
        )
        return
    corr = df[kpi_names].corr(method="pearson")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(10, 8))
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", center=0, square=True)
    plt.title(
        "Pearson Correlation -- Core KPIs (latest year, all 92 companies, sanity-bound masked)"
    )
    plt.tight_layout()
    plt.savefig(REPORTS_DIR / "correlation_heatmap.png", dpi=150)
    plt.close()
    logger.info("reports/correlation_heatmap.png saved")


def detect_outliers(
    df: pd.DataFrame, kpi_names: list, z_threshold: float = 3.0
) -> pd.DataFrame:
    """Detect outliers."""
    rows = []
    for sector, grp in df.groupby("broad_sector"):
        for kpi in kpi_names:
            values = grp[kpi].dropna()
            if len(values) < 2:
                continue
            mean, std = values.mean(), values.std()
            if std == 0 or pd.isna(std):
                continue
            for _, r in grp.iterrows():
                if pd.isna(r[kpi]):
                    continue
                z = (r[kpi] - mean) / std
                if abs(z) > z_threshold:
                    rows.append(
                        {
                            "company_id": r["company_id"],
                            "metric": kpi,
                            "value": r[kpi],
                            "z_score": round(z, 2),
                            "sector": sector,
                            "sector_mean": round(mean, 2),
                            "sector_std": round(std, 2),
                        }
                    )
    return pd.DataFrame(rows)


def generate_portfolio_stats(df: pd.DataFrame, kpi_names: list) -> pd.DataFrame:
    """Generate portfolio stats."""
    rows = []
    for kpi in kpi_names:
        values = df[kpi].dropna()
        rows.append(
            {
                "metric": kpi,
                "P10": round(np.percentile(values, 10), 2),
                "P25": round(np.percentile(values, 25), 2),
                "P50": round(np.percentile(values, 50), 2),
                "P75": round(np.percentile(values, 75), 2),
                "P90": round(np.percentile(values, 90), 2),
                "Mean": round(values.mean(), 2),
                "Std": round(values.std(), 2),
                "n": len(values),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    """Main."""
    conn = get_connection()
    try:
        kpi_map = resolve_kpi_columns(conn)
        df = load_latest_kpis(conn, kpi_map)
    finally:
        conn.close()

    df = apply_ratio_sanity_bounds(df)
    df = apply_known_anomaly_exclusions(df)
    kpi_names = list(kpi_map.keys())

    generate_correlation_heatmap(df, kpi_names)

    outliers = detect_outliers(df, kpi_names)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    outliers.to_csv(OUTPUT_DIR / "outlier_report.csv", index=False)
    logger.info("output/outlier_report.csv written -- %d flagged rows", len(outliers))
    if len(outliers):
        print(
            "\nOutliers flagged (|Z| > 3, sector-relative, ROE/ROCE/ROA masked, HINDALCO OPM excluded):"
        )
        print(outliers.to_string(index=False))

    stats = generate_portfolio_stats(df, kpi_names)
    stats.to_csv(OUTPUT_DIR / "portfolio_stats.csv", index=False)
    logger.info("output/portfolio_stats.csv written -- %d metrics", len(stats))
    print("\nPortfolio statistics:")
    print(stats.to_string(index=False))


if __name__ == "__main__":
    main()
