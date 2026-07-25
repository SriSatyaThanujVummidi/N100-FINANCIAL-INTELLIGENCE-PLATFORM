"""Radar chart generator — Sprint 3, Day 19.

8-axis radar/polar chart per company (spec Module 9, feature 4.2):
  ROE, ROCE, NPM, D/E, FCF score, PAT CAGR 5yr, Revenue CAGR 5yr,
  Composite Score.

Design decision: reuses Day 17's compute_sector_relative_composite_score()
sub-score columns (already sector-relative, winsorized, scaled 0-100)
instead of raw metrics — raw ROE(%)/D/E(ratio)/FCF(Rs Cr)/Composite(0-100)
span incompatible scales that would make a single radar meaningless.
This also carries over Day 13's sanity-bound masking for free (HAL, BEL,
INDIGO, ICICIPRULI, HDFCLIFE already NaN on the affected axes).

"FCF score" (spec's literal wording) = fcf_positive_flag (0/100), matching
the composite formula's own "FCF>0 flag" sub-input — flagged for team
lead review as an interpretation, not fcf_cagr_5yr_score.

D/E axis uses de_score directly (already inverted: D/E=0 -> 100,
D/E>=5 -> 0) so "outward = good" holds on every axis consistently.

Peer group average EXCLUDES the company itself (peers, not
peers-plus-self). Companies with no peer group (36/92, per Day 18) get
the Nifty-100-wide average as their reference overlay instead — same
8-axis shape, different comparison baseline (documented interpretation
of the spec's "single-metric standalone chart... Nifty 100 average as
reference" wording).

Missing axis values (NaN, from sanity-bound masking) are plotted as 0
with a footer annotation naming which metrics are unavailable and why —
consistent with this project's rule of never silently hiding a data
quality issue.
"""

from __future__ import annotations

import os
import sqlite3

import matplotlib

matplotlib.use("Agg")  # headless — no display needed, just save PNGs
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.screener.composite_score import compute_sector_relative_composite_score
from src.screener.engine import load_screener_universe

DB_PATH = "data/nifty100.db"
OUTPUT_DIR = "reports/radar_charts"

RADAR_AXES = [
    ("ROE", "return_on_equity_pct_score"),
    ("ROCE", "return_on_capital_employed_pct_score"),
    ("NPM", "net_profit_margin_pct_score"),
    ("D/E", "de_score"),
    ("FCF", "fcf_positive_flag"),
    ("PAT CAGR 5yr", "pat_cagr_5yr_score"),
    ("Revenue CAGR 5yr", "revenue_cagr_5yr_score"),
    ("Composite", "composite_score_sector_relative"),
]


def build_scored_universe(conn: sqlite3.Connection) -> pd.DataFrame:
    """Load the screener universe with Day 17's sector-relative scores,
    plus peer_group_name for each company (Day 18's peer_groups table)."""
    universe = load_screener_universe(conn)
    universe = compute_sector_relative_composite_score(universe, conn)

    peer_groups = pd.read_sql_query(
        "SELECT company_id, peer_group_name FROM peer_groups", conn
    )
    universe = universe.merge(peer_groups, on="company_id", how="left")

    companies = pd.read_sql_query(
        "SELECT id AS company_id, company_name FROM companies", conn
    )
    universe = universe.merge(companies, on="company_id", how="left")

    return universe


def get_axis_values(row: pd.Series) -> list[float]:
    """Extract the 8 axis values for one company, in RADAR_AXES order.
    Missing (NaN) values are returned as NaN here — plotting logic
    decides how to render them (0 + footer note), not this function."""
    return [row.get(col) for _, col in RADAR_AXES]


def compute_peer_average(
    universe: pd.DataFrame, peer_group_name: str, exclude_company_id: str
) -> list[float]:
    """Average of each axis across the peer group, EXCLUDING the company
    itself. Uses nanmean so a sanity-flagged peer's NaN doesn't wipe out
    the whole group's average for that axis."""
    peers = universe[
        (universe["peer_group_name"] == peer_group_name)
        & (universe["company_id"] != exclude_company_id)
    ]
    return [
        float(np.nanmean(peers[col])) if peers[col].notna().any() else float("nan")
        for _, col in RADAR_AXES
    ]


def compute_universe_average(
    universe: pd.DataFrame, exclude_company_id: str
) -> list[float]:
    """Nifty-100-wide average, for companies with no peer group (Day 18:
    36/92 companies)."""
    others = universe[universe["company_id"] != exclude_company_id]
    return [
        float(np.nanmean(others[col])) if others[col].notna().any() else float("nan")
        for _, col in RADAR_AXES
    ]


def get_axis_angles(n: int) -> np.ndarray:
    """n evenly-spaced angles around a circle, PLUS the first angle
    repeated at the end to close the polygon when plotted."""
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()
    angles += angles[:1]
    return np.array(angles)


def close_values(values: list[float]) -> list[float]:
    """Repeat the first value at the end, matching get_axis_angles()'s
    closed-loop angle array — required for matplotlib to draw a closed
    polygon rather than leaving a gap."""
    return values + values[:1]


def plot_radar_chart(
    company_id: str,
    company_name: str,
    own_values: list[float],
    avg_values: list[float],
    avg_label: str,
    output_path: str,
) -> None:
    """Render one company's radar chart and save as PNG."""
    labels = [label for label, _ in RADAR_AXES]
    n = len(labels)
    angles = get_axis_angles(n)

    missing_axes = [labels[i] for i, v in enumerate(own_values) if pd.isna(v)]
    own_plot = close_values([0.0 if pd.isna(v) else v for v in own_values])
    avg_plot = close_values([0.0 if pd.isna(v) else v for v in avg_values])

    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw={"projection": "polar"})

    ax.plot(angles, own_plot, color="#2166AC", linewidth=2, label=company_id)
    ax.fill(angles, own_plot, color="#2166AC", alpha=0.25)

    ax.plot(
        angles,
        avg_plot,
        color="#B2182B",
        linewidth=1.5,
        linestyle="--",
        label=avg_label,
    )

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=11)
    ax.set_ylim(0, 100)
    ax.set_yticks([25, 50, 75, 100])
    ax.set_yticklabels(["25", "50", "75", "100"], fontsize=8)

    title = f"{company_id} — {company_name}" if company_name else company_id
    ax.set_title(title, fontsize=13, fontweight="bold", pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.1), fontsize=9)

    if missing_axes:
        fig.text(
            0.5,
            0.02,
            f"Data unavailable (plotted as 0): {', '.join(missing_axes)} — "
            f"see PROGRESS.md Day 13/17 sanity-bound findings.",
            ha="center",
            fontsize=8,
            color="#666666",
            wrap=True,
        )

    plt.tight_layout()
    plt.savefig(output_path, dpi=120, bbox_inches="tight")
    plt.close(fig)


def generate_company_chart(
    company_id: str, universe: pd.DataFrame, output_dir: str = OUTPUT_DIR
) -> str:
    """Generate and save one company's radar chart. Returns the output path."""
    row = universe[universe["company_id"] == company_id].iloc[0]
    own_values = get_axis_values(row)

    peer_group_name = row.get("peer_group_name")
    if pd.notna(peer_group_name):
        avg_values = compute_peer_average(universe, peer_group_name, company_id)
        avg_label = f"{peer_group_name} avg"
    else:
        avg_values = compute_universe_average(universe, company_id)
        avg_label = "Nifty 100 avg"

    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{company_id}_radar.png")
    plot_radar_chart(
        company_id,
        row.get("company_name", ""),
        own_values,
        avg_values,
        avg_label,
        output_path,
    )
    return output_path


def generate_all_radar_charts() -> None:
    """Generate all radar charts."""
    conn = sqlite3.connect(DB_PATH)
    universe = build_scored_universe(conn)

    for i, company_id in enumerate(universe["company_id"], start=1):
        path = generate_company_chart(company_id, universe)
        if i % 10 == 0 or i == len(universe):
            print(f"[{i}/{len(universe)}] {path}")

    conn.close()
    print(f"\nDone: {len(universe)} radar charts written to {OUTPUT_DIR}/")


if __name__ == "__main__":
    generate_all_radar_charts()
