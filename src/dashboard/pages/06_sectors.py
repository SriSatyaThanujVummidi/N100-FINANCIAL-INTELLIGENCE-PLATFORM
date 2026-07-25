"""Sector Analysis screen — Day 25.

Sector dropdown -> bubble chart (X=Revenue, Y=ROE, size=Market Cap,
colour=sub_sector) + sector median KPI bar chart below.
"""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import plotly.express as px
import streamlit as st

from src.dashboard.utils.db import (
    get_companies,
    get_latest_market_cap_all,
    get_latest_pl_all,
    get_latest_ratios,
)

st.set_page_config(page_title="Sector Analysis | Nifty 100", layout="wide")

ROE_ROCE_BOUND = 500.0

# Spec Section 6.1's 11 named broad sectors — used to surface exactly which
# one is missing from the real `sectors` table (Day 23's "10 vs 11" finding),
# rather than leaving it as an unexplained count.
SPEC_SECTORS = {
    "Financials",
    "Energy",
    "Information Technology",
    "Consumer Discretionary",
    "Consumer Staples",
    "Healthcare",
    "Materials",
    "Industrials",
    "Communication Services",
    "Real Estate",
    "Conglomerates / Other",
}

st.header("🏭 Sector Analysis")

companies_df = get_companies()
ratios_df = get_latest_ratios()
pl_df = get_latest_pl_all()
mcap_df = get_latest_market_cap_all()

# ---- Build the merged, per-company analysis table ------------------------
base = companies_df[["id", "company_name", "broad_sector", "sub_sector"]].copy()
base = base.merge(
    ratios_df[["company_id", "return_on_equity_pct"]],
    left_on="id",
    right_on="company_id",
    how="left",
)
base = base.merge(
    pl_df[["company_id", "sales"]], on="company_id", how="left", suffixes=("", "_pl")
)
base = base.merge(
    mcap_df[["company_id", "market_cap_crore"]], on="company_id", how="left"
)
base["roe_masked"] = base["return_on_equity_pct"].where(
    base["return_on_equity_pct"].abs() <= ROE_ROCE_BOUND
)

present_sectors = set(base["broad_sector"].dropna().unique())
missing_sectors = SPEC_SECTORS - present_sectors
if missing_sectors:
    st.caption(
        f"⚠️ Sector(s) present in spec Section 6.1 but not found in the "
        f"`sectors` table: **{', '.join(sorted(missing_sectors))}**. "
        "Confirms Day 23's 10-vs-11 finding — root cause not yet diagnosed."
    )

sector_list = sorted(base["broad_sector"].dropna().unique())
if not sector_list:
    st.warning("No sector data available.")
    st.stop()

selected_sector = st.selectbox("Sector", sector_list)

sector_df = base[base["broad_sector"] == selected_sector].dropna(
    subset=["sales", "roe_masked"]
)

st.subheader(f"{selected_sector} — Revenue vs ROE")
if sector_df.empty:
    st.info("No companies with complete Revenue + ROE data in this sector.")
else:
    fig_bubble = px.scatter(
        sector_df,
        x="sales",
        y="roe_masked",
        size="market_cap_crore",
        color="sub_sector",
        hover_name="company_name",
        labels={
            "sales": "Revenue (₹Cr, latest year)",
            "roe_masked": "ROE (%)",
            "market_cap_crore": "Market Cap (₹Cr)",
            "sub_sector": "Sub-Sector",
        },
        size_max=45,
    )
    fig_bubble.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=500)
    st.plotly_chart(fig_bubble, use_container_width=True)

    n_dropped = len(base[base["broad_sector"] == selected_sector]) - len(sector_df)
    if n_dropped > 0:
        st.caption(
            f"{n_dropped} compan(y/ies) in this sector omitted from the "
            "bubble chart due to missing Revenue, ROE, or the ROE sanity bound."
        )

st.divider()

# ---- Sector median KPI bar chart -----------------------------------------
st.subheader("Sector Median KPIs — All Sectors")
sector_medians = (
    base.groupby("broad_sector")
    .agg(
        median_roe=("roe_masked", "median"),
        median_revenue=("sales", "median"),
        company_count=("id", "count"),
    )
    .reset_index()
    .sort_values("median_roe", ascending=False)
)
fig_medians = px.bar(
    sector_medians,
    x="broad_sector",
    y="median_roe",
    hover_data=["median_revenue", "company_count"],
    labels={"broad_sector": "Sector", "median_roe": "Median ROE (%)"},
)
fig_medians.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=400)
st.plotly_chart(fig_medians, use_container_width=True)
