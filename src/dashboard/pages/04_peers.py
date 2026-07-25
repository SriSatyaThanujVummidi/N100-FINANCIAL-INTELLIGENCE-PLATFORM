"""Peer Comparison screen — Day 24.

Peer group dropdown (11 groups), radar chart (selected company vs peer
group average, 8 axes via percentile_rank from Day 18's peer_percentiles
table so incompatible raw scales don't distort the shape — same reasoning
as Day 19's radar_charts.py), side-by-side KPI table with the benchmark
company row highlighted.
"""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.dashboard.utils.db import (
    get_companies,
    get_latest_ratios,
    get_peer_percentiles,
    get_peers,
)

st.set_page_config(page_title="Peer Comparison | Nifty 100", layout="wide")

st.header("👥 Peer Comparison")

percentiles_all = get_peer_percentiles()
if percentiles_all.empty:
    st.error(
        "peer_percentiles table is empty — check Day 18's src/analytics/peer.py has been run."
    )
    st.stop()

groups = sorted(percentiles_all["peer_group_name"].unique().tolist())
selected_group = st.selectbox("Peer group", groups)

group_percentiles = percentiles_all[
    percentiles_all["peer_group_name"] == selected_group
]
group_members = get_peers(selected_group)  # company_id, is_benchmark
companies_df = get_companies()
ratios_df = get_latest_ratios()

member_ids = group_members["company_id"].unique().tolist()
member_info = companies_df[companies_df["id"].isin(member_ids)][["id", "company_name"]]

if member_info.empty:
    st.warning("No members found for this peer group.")
    st.stop()

member_info["label"] = (
    member_info["id"] + " — " + member_info["company_name"].fillna("")
)
selected_label = st.selectbox("Company", member_info["label"].tolist())
selected_ticker = selected_label.split(" — ")[0]

st.divider()

# ---- Radar chart: selected company vs peer group average ----------------
st.subheader(f"{selected_ticker} vs {selected_group} Average")

# Map available metric strings to 8 target axes (spec Module 9, feature 4.2)
AXIS_KEYWORDS = {
    "ROE": ["return_on_equity", "roe"],
    "ROCE": ["return_on_capital_employed", "roce"],
    "NPM": ["net_profit_margin", "npm"],
    "D/E": ["debt_to_equity", "d/e", "de"],
    "FCF": ["free_cash_flow", "fcf"],
    "PAT CAGR 5yr": ["pat_cagr", "pat"],
    "Revenue CAGR 5yr": ["revenue_cagr", "rev_cagr"],
    "EPS CAGR 5yr": ["eps_cagr", "eps"],
}
available_metrics = group_percentiles["metric"].unique().tolist()

axis_to_metric = {}
for axis, keywords in AXIS_KEYWORDS.items():
    match = next(
        (m for m in available_metrics if any(kw in m.lower() for kw in keywords)), None
    )
    if match:
        axis_to_metric[axis] = match

if not axis_to_metric:
    st.warning("No metrics could be matched for the radar chart axes.")
else:
    if len(axis_to_metric) < 8:
        missing_axes = [a for a in AXIS_KEYWORDS if a not in axis_to_metric]
        st.caption(
            f"⚠️ {len(axis_to_metric)}/8 axes available — missing: {', '.join(missing_axes)}."
        )

    axes = list(axis_to_metric.keys())
    company_vals = []
    group_avg_vals = []
    for axis in axes:
        metric_name = axis_to_metric[axis]
        metric_rows = group_percentiles[group_percentiles["metric"] == metric_name]
        company_row = metric_rows[metric_rows["company_id"] == selected_ticker]
        company_pctile = (
            float(company_row["percentile_rank"].iloc[0]) * 100
            if not company_row.empty
            and pd.notna(company_row["percentile_rank"].iloc[0])
            else 0.0
        )
        group_avg = metric_rows["percentile_rank"].dropna().mean()
        group_avg_pctile = float(group_avg) * 100 if pd.notna(group_avg) else 0.0
        company_vals.append(company_pctile)
        group_avg_vals.append(group_avg_pctile)

    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=company_vals + [company_vals[0]],
            theta=axes + [axes[0]],
            fill="toself",
            name=selected_ticker,
        )
    )
    fig.add_trace(
        go.Scatterpolar(
            r=group_avg_vals + [group_avg_vals[0]],
            theta=axes + [axes[0]],
            fill="toself",
            name=f"{selected_group} Average",
            opacity=0.5,
        )
    )
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=True,
        margin=dict(t=30, b=10, l=30, r=30),
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "Axes show each metric's within-group percentile rank (0-100), not raw "
        "values — raw ROE(%)/D/E(ratio)/FCF(₹Cr) scales are incompatible on a "
        "single radar, same convention as Day 19's static radar charts."
    )

st.divider()

# ---- Side-by-side KPI table, benchmark row highlighted -----------------
st.subheader(f"{selected_group} — Side-by-Side Comparison")

group_ratios = ratios_df[ratios_df["company_id"].isin(member_ids)].copy()
group_ratios = group_ratios.merge(
    companies_df[["id", "company_name"]],
    left_on="company_id",
    right_on="id",
    how="left",
)
group_ratios = group_ratios.merge(
    group_members[["company_id", "is_benchmark"]], on="company_id", how="left"
)
group_ratios["is_benchmark"] = group_ratios["is_benchmark"].fillna(False)

display_candidates = [
    "company_id",
    "company_name",
    "is_benchmark",
    "return_on_equity_pct",
    "return_on_capital_employed_pct",
    "net_profit_margin_pct",
    "debt_to_equity",
    "free_cash_flow_cr",
    "revenue_cagr_5yr",
    "pat_cagr_5yr",
]
display_cols = [c for c in display_candidates if c in group_ratios.columns]
table_df = group_ratios[display_cols].sort_values(
    "return_on_equity_pct" if "return_on_equity_pct" in display_cols else "company_id",
    ascending=False,
    na_position="last",
)


def highlight_benchmark(row):
    """Highlight benchmark."""
    if row.get("is_benchmark"):
        return ["background-color: #4a3b00"] * len(row)
    return [""] * len(row)


table_display = table_df.drop(columns=["is_benchmark"]).copy()
table_display.columns = [
    c.replace("_pct", " %").replace("_", " ").title() for c in table_display.columns
]

try:
    styled = table_df.style.apply(highlight_benchmark, axis=1)
    styled = styled.hide(axis="index").hide(["is_benchmark"], axis="columns")
    st.dataframe(styled, use_container_width=True)
except Exception:
    # Fallback if the installed pandas/Streamlit version doesn't support
    # this Styler chain — mark the benchmark row with a star instead.
    table_display.insert(0, "⭐", table_df["is_benchmark"].map({True: "⭐", False: ""}))
    st.dataframe(table_display, use_container_width=True, hide_index=True)

st.caption(
    "⭐ / highlighted row = benchmark company for this peer group (peer_groups.is_benchmark)."
)
