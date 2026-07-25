"""Trend Analysis screen — Day 25.

Company search + multi-metric overlay (up to 3 metrics) — 10-year line
chart with YoY % change annotated at each data point.
"""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.dashboard.utils.db import get_companies, get_ratios

st.set_page_config(page_title="Trend Analysis | Nifty 100", layout="wide")

# Mirrors Day 13's Option B sanity bound — applied if ROE/ROCE selected.
ROE_ROCE_BOUND = 500.0
MASKED_COLUMNS = {"return_on_equity_pct", "return_on_capital_employed_pct"}

METRIC_OPTIONS = {
    "ROE (%)": "return_on_equity_pct",
    "ROCE (%)": "return_on_capital_employed_pct",
    "Net Profit Margin (%)": "net_profit_margin_pct",
    "Operating Profit Margin (%)": "operating_profit_margin_pct",
    "D/E": "debt_to_equity",
    "Free Cash Flow (₹Cr)": "free_cash_flow_cr",
    "Revenue CAGR 5yr (%)": "revenue_cagr_5yr",
    "PAT CAGR 5yr (%)": "pat_cagr_5yr",
    "Asset Turnover": "asset_turnover",
    "Interest Coverage": "interest_coverage",
}

st.header("📈 Trend Analysis")

companies_df = get_companies()

search_term = st.text_input(
    "Search by company name or ticker", placeholder="e.g. INFY or Infosys"
)
if search_term.strip():
    term = search_term.strip().upper()
    matches = companies_df[
        companies_df["id"].str.upper().str.contains(term, na=False)
        | companies_df["company_name"].str.upper().str.contains(term, na=False)
    ]
else:
    matches = companies_df

if matches.empty:
    st.warning("Ticker not found — please try another")
    st.stop()

matches = matches.copy()
matches["display_label"] = matches["id"] + " — " + matches["company_name"].fillna("")
selected_label = st.selectbox("Select company", matches["display_label"].tolist())
selected_ticker = selected_label.split(" — ")[0]

selected_metric_labels = st.multiselect(
    "Metrics to overlay (up to 3)",
    options=list(METRIC_OPTIONS.keys()),
    default=["ROE (%)"],
    max_selections=3,
)

if not selected_metric_labels:
    st.info("Select at least one metric to see the trend chart.")
    st.stop()

ratios_df = get_ratios(ticker=selected_ticker)

if ratios_df.empty:
    st.warning(f"No financial_ratios data found for {selected_ticker}.")
    st.stop()

ratios_recent = ratios_df.sort_values("year").tail(10).reset_index(drop=True)

fig = go.Figure()
for label in selected_metric_labels:
    col = METRIC_OPTIONS[label]
    if col not in ratios_recent.columns:
        st.caption(
            f"⚠️ Column `{col}` not found in financial_ratios — skipping {label}."
        )
        continue

    series = pd.to_numeric(ratios_recent[col], errors="coerce")
    if col in MASKED_COLUMNS:
        series = series.where(series.abs() <= ROE_ROCE_BOUND)

    fig.add_trace(
        go.Scatter(
            x=ratios_recent["year"],
            y=series,
            name=label,
            mode="lines+markers",
        )
    )

    # YoY % change annotation on each point (skip first point — no prior year)
    yoy_pct = series.pct_change() * 100
    for i in range(1, len(ratios_recent)):
        if pd.isna(yoy_pct.iloc[i]) or pd.isna(series.iloc[i]):
            continue
        fig.add_annotation(
            x=ratios_recent["year"].iloc[i],
            y=series.iloc[i],
            text=f"{yoy_pct.iloc[i]:+.1f}%",
            showarrow=False,
            yshift=14,
            font=dict(size=9),
        )

fig.update_layout(
    xaxis_title="Fiscal Year",
    yaxis_title="Value",
    margin=dict(t=20, b=10, l=10, r=10),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    height=550,
)
st.plotly_chart(fig, use_container_width=True)

# Per-metric "no data" callout — a metric with zero plottable points (e.g.
# ROE/ROCE/D/E for SBIN, which has zero balancesheet rows per Day 6) would
# otherwise render as a silent blank line with no explanation.
for label in selected_metric_labels:
    col = METRIC_OPTIONS.get(label)
    if col not in ratios_recent.columns:
        continue
    series_check = pd.to_numeric(ratios_recent[col], errors="coerce")
    if col in MASKED_COLUMNS:
        series_check = series_check.where(series_check.abs() <= ROE_ROCE_BOUND)
    if series_check.dropna().empty:
        st.warning(
            f"⚠️ **{label}** has no plottable data for {selected_ticker} — "
            "likely a balance-sheet-dependent metric for a company with "
            "missing balance sheet rows (e.g. SBIN, Day 6 finding), or a "
            "P&L-dependent metric for a company with no reported history."
        )

if len(ratios_recent) < 10:
    st.caption(
        f"Only {len(ratios_recent)} year(s) of history available for "
        f"{selected_ticker} — chart shows all available years."
    )

if any(METRIC_OPTIONS[m] in MASKED_COLUMNS for m in selected_metric_labels):
    st.caption(
        f"⚠️ ROE/ROCE points with |value| > {ROE_ROCE_BOUND:.0f}% are hidden "
        "as implausible (Day 13 sanity bound)."
    )
