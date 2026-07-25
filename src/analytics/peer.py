"""Peer comparison engine — Sprint 3, Day 18.

Computes PERCENT_RANK for 10 metrics within each of the 11 real peer
groups (spec Module 9, feature 4.1). Populates peer_percentiles table.

Schema confirmed Day 18 (PRAGMA check): peer_groups is
(id, peer_group_name, company_id, is_benchmark) — one row per
company-per-group, NOT the spec's assumed comma-separated members format
(documented back on Day 1). 56/92 companies belong to exactly one of 11
groups; no company belongs to more than one (confirmed via
day18_diagnose_peer_groups.py). The remaining 36/92 get "No peer group
assigned" (spec Module 9, feature 4.1's explicit requirement) rather
than an error.

D/E is inverted per spec: 1 - PERCENT_RANK(debt_to_equity), so LOWER debt
gets a HIGHER percentile rank (conventionally "good" = high percentile,
consistent with every other metric here).

Day 13 sanity-bound integration: companies flagged by
src.analytics.edge_cases.flag_implausible_ratio() (HAL, BEL, INDIGO,
ICICIPRULI, HDFCLIFE — same anomaly family wired into Day 17's composite
score) have return_on_equity_pct/return_on_capital_employed_pct masked to
NaN before ranking, for the same reason: an implausible ratio would
distort not just its own percentile but the whole group's rank ordering
for every genuine peer. Confirmed via day18_diagnose_flagged_in_peers.py
whether any flagged company sits inside a real peer group before this
was applied — not assumed.
"""

from __future__ import annotations

import sqlite3

import pandas as pd

from src.analytics.edge_cases import flag_implausible_ratio

PEER_METRICS = {
    "return_on_equity_pct": "higher_better",
    "return_on_capital_employed_pct": "higher_better",
    "net_profit_margin_pct": "higher_better",
    "debt_to_equity": "lower_better",  # inverted below
    "free_cash_flow_cr": "higher_better",
    "pat_cagr_5yr": "higher_better",
    "revenue_cagr_5yr": "higher_better",
    "eps_cagr_5yr": "higher_better",
    "interest_coverage": "higher_better",
    "asset_turnover": "higher_better",
}

SANITY_CHECK_METRICS = ["return_on_equity_pct", "return_on_capital_employed_pct"]


def load_peer_universe(conn: sqlite3.Connection) -> pd.DataFrame:
    """Build the per-company-latest-year universe joined to peer_groups.

    Uses the same per-company latest-year join pattern as
    src/screener/engine.py's load_screener_universe() (Day 15 fix for
    SIEMENS's non-March fiscal year-end) — NOT a single shared year
    filter.
    """
    fr = pd.read_sql_query(
        """
        SELECT fr.* FROM financial_ratios fr
        INNER JOIN (
            SELECT company_id, MAX(year) AS latest_year
            FROM financial_ratios GROUP BY company_id
        ) latest
        ON fr.company_id = latest.company_id AND fr.year = latest.latest_year
        """,
        conn,
    )

    peer_groups = pd.read_sql_query(
        "SELECT peer_group_name, company_id, is_benchmark FROM peer_groups", conn
    )

    df = fr.merge(peer_groups, on="company_id", how="left")

    # Day 13 sanity-bound masking, same scope as Day 17's composite score.
    df["sanity_flagged"] = df.apply(
        lambda r: any(
            flag_implausible_ratio(m, r.get(m)) for m in SANITY_CHECK_METRICS
        ),
        axis=1,
    )
    for metric in SANITY_CHECK_METRICS:
        df.loc[df["sanity_flagged"], metric] = None

    return df


def compute_peer_percentiles(df: pd.DataFrame) -> pd.DataFrame:
    """Long-format output: company_id, peer_group_name, metric, value,
    percentile_rank, year. One row per (company, metric) for every
    company that belongs to a peer group. Companies with no peer group
    are excluded here — callers use get_peer_percentile() / the
    "No peer group assigned" message for those, per spec 4.1.
    """
    grouped = df[df["peer_group_name"].notna()].copy()

    records = []
    for group_name, group_df in grouped.groupby("peer_group_name"):
        for metric, direction in PEER_METRICS.items():
            ranks = group_df[metric].rank(pct=True, na_option="keep")
            if direction == "lower_better":
                ranks = 1 - ranks

            for idx, company_id in group_df["company_id"].items():
                value = group_df.loc[idx, metric]
                percentile = ranks.loc[idx]
                records.append(
                    {
                        "company_id": company_id,
                        "peer_group_name": group_name,
                        "metric": metric,
                        "value": value,
                        "percentile_rank": percentile,
                        "year": group_df.loc[idx, "year"],
                    }
                )

    return pd.DataFrame(records)


def get_peer_percentile(
    company_id: str, percentiles_df: pd.DataFrame
) -> pd.DataFrame | str:
    """Spec Module 9, feature 4.1: for a company not in any peer group,
    return the exact message 'No peer group assigned' rather than raising
    an error. Otherwise return that company's percentile rows."""
    rows = percentiles_df[percentiles_df["company_id"] == company_id]
    if rows.empty:
        return "No peer group assigned"
    return rows


def create_peer_percentiles_table(conn: sqlite3.Connection) -> None:
    """Idempotent: drop and recreate, matching populate_financial_ratios.py's
    convention from Sprint 2 (Day 12)."""
    conn.execute("DROP TABLE IF EXISTS peer_percentiles")
    conn.execute("""
        CREATE TABLE peer_percentiles (
            company_id TEXT NOT NULL,
            peer_group_name TEXT NOT NULL,
            metric TEXT NOT NULL,
            value REAL,
            percentile_rank REAL,
            year TEXT NOT NULL
        )
        """)
    conn.commit()


def populate_peer_percentiles(conn: sqlite3.Connection) -> pd.DataFrame:
    """Full pipeline: load universe, compute percentiles, write table."""
    universe = load_peer_universe(conn)
    percentiles = compute_peer_percentiles(universe)

    create_peer_percentiles_table(conn)
    percentiles.to_sql("peer_percentiles", conn, if_exists="append", index=False)
    conn.commit()

    return percentiles


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.INFO)

    DB_PATH = "data/nifty100.db"
    with sqlite3.connect(DB_PATH) as conn:
        result = populate_peer_percentiles(conn)
        print(f"peer_percentiles populated: {len(result)} rows")
        print(f"Companies covered: {result['company_id'].nunique()}")
        print(f"Peer groups: {result['peer_group_name'].nunique()}")
