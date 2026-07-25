"""Home / Overview screen — Day 23.

Portfolio-wide KPI tiles, sector breakdown donut, top-5 by composite
quality score. Year selector uses calendar years (spec: 2019-2024) mapped
to each company's own latest fiscal-year-end on or before that year via
get_ratios_as_of_calendar_year() — handles SIEMENS/NESTLEIND-style non-
March fiscal year-ends correctly (Day 15 finding).
"""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import pandas as pd
import plotly.express as px
import streamlit as st

from src.dashboard.utils.db import (
    get_companies,
    get_ratios_as_of_calendar_year,
    get_valuation,
)

st.set_page_config(page_title="Home | Nifty 100", layout="wide")

# Generic sanity bound mirroring Day 13's Option B (flag_implausible_ratio()
# in src/analytics/edge_cases.py). Applied here so HAL/BEL/INDIGO/ICICIPRULI/
# HDFCLIFE's implausible ROE/ROCE don't skew the portfolio-wide Average ROE
# tile. If the real bound in edge_cases.py differs from 500%, update ROE_ROCE_BOUND.
ROE_ROCE_BOUND = 500.0


def mask_implausible(series: pd.Series) -> pd.Series:
    """Mask implausible."""
    series = pd.to_numeric(series, errors="coerce")
    return series.where(series.abs() <= ROE_ROCE_BOUND)


def fmt(val, decimals=1, suffix=""):
    """Fmt."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "N/A"
    try:
        if pd.isna(val):
            return "N/A"
    except TypeError:
        pass
    return f"{val:.{decimals}f}{suffix}"


st.header("🏠 Home / Overview")

# ---- Year selector (sidebar) --------------------------------------------
YEAR_OPTIONS = [2024, 2023, 2022, 2021, 2020, 2019]
selected_year = st.sidebar.selectbox("Year", YEAR_OPTIONS, index=0)
st.caption(
    f"Showing each company's latest reported fiscal year on or before "
    f"December {selected_year}. Companies with a Sep/Dec/June fiscal "
    f"year-end (e.g. SIEMENS, NESTLEIND) are included via their own "
    f"nearest year-end, not forced into a March-only filter."
)

companies_df = get_companies()
ratios_year = get_ratios_as_of_calendar_year(selected_year)
valuation_df = get_valuation()
valuation_year = (
    valuation_df[valuation_df["year"] == selected_year]
    if not valuation_df.empty
    else pd.DataFrame()
)

if ratios_year.empty:
    st.warning(f"No financial_ratios data available on or before {selected_year}.")
    st.stop()

# ---- KPI tiles ------------------------------------------------------------
roe_masked = mask_implausible(
    ratios_year.get("return_on_equity_pct", pd.Series(dtype=float))
)
avg_roe = roe_masked.dropna().mean()

median_pe = (
    valuation_year["pe_ratio"].dropna().median()
    if "pe_ratio" in valuation_year.columns and not valuation_year.empty
    else None
)
median_de = ratios_year.get("debt_to_equity", pd.Series(dtype=float)).dropna().median()
total_companies = len(companies_df)
median_rev_cagr = (
    ratios_year.get("revenue_cagr_5yr", pd.Series(dtype=float)).dropna().median()
)

if "total_debt_cr" in ratios_year.columns:
    debt_free_count = int((ratios_year["total_debt_cr"] == 0).sum())
else:
    debt_free_count = int(
        (ratios_year.get("debt_to_equity", pd.Series(dtype=float)) == 0).sum()
    )

col1, col2, col3 = st.columns(3)
col1.metric("Average ROE", fmt(avg_roe, 1, "%"))
col2.metric("Median P/E", fmt(median_pe, 1, "×"))
col3.metric("Median D/E", fmt(median_de, 2, "×"))

col4, col5, col6 = st.columns(3)
col4.metric("Total Companies", total_companies)
col5.metric("Median Revenue CAGR (5yr)", fmt(median_rev_cagr, 1, "%"))
col6.metric("Debt-Free Companies", debt_free_count)

st.caption(
    "ROE aggregate excludes companies flagged for implausible ratios "
    f"(|ROE| > {ROE_ROCE_BOUND:.0f}%) — see Day 13's edge case log."
)

st.divider()

# ---- Sector breakdown donut -------------------------------------------
st.subheader("Sector Breakdown")
sector_counts = (
    companies_df.dropna(subset=["broad_sector"])
    .groupby("broad_sector")
    .size()
    .reset_index(name="company_count")
    .sort_values("company_count", ascending=False)
)
if sector_counts.empty:
    st.info("No sector data available — check the sectors table load.")
else:
    fig = px.pie(
        sector_counts,
        names="broad_sector",
        values="company_count",
        hole=0.45,
    )
    fig.update_traces(textinfo="label+value")
    fig.update_layout(margin=dict(t=10, b=10, l=10, r=10))
    st.plotly_chart(fig, use_container_width=True)
    if len(sector_counts) != 11:
        st.caption(
            f"Note: {len(sector_counts)} distinct sectors found in the "
            "sectors table (spec Section 6.1 defines 11) — under review."
        )

st.divider()

# ---- Top-5 by composite quality score ----------------------------------
st.subheader("Top 5 Companies — Composite Quality Score")
if "composite_quality_score" not in ratios_year.columns:
    st.info(
        "composite_quality_score column not found in financial_ratios — "
        "confirm Sprint 2's populate_financial_ratios.py has been run."
    )
else:
    merged = ratios_year.merge(
        companies_df[["id", "company_name", "broad_sector"]],
        left_on="company_id",
        right_on="id",
        how="left",
    )
    top5 = (
        merged.dropna(subset=["composite_quality_score"])
        .sort_values("composite_quality_score", ascending=False)
        .head(5)
    )
    if top5.empty:
        st.info("No companies have a composite quality score for this year.")
    else:
        display_cols = [
            "company_id",
            "company_name",
            "broad_sector",
            "composite_quality_score",
            "return_on_equity_pct",
        ]
        display_df = top5[[c for c in display_cols if c in top5.columns]].copy()
        display_df["composite_quality_score"] = display_df[
            "composite_quality_score"
        ].round(2)
        if "return_on_equity_pct" in display_df.columns:
            display_df["return_on_equity_pct"] = display_df[
                "return_on_equity_pct"
            ].round(2)
        display_df.columns = [c.replace("_", " ").title() for c in display_df.columns]
        st.dataframe(display_df, use_container_width=True, hide_index=True)
