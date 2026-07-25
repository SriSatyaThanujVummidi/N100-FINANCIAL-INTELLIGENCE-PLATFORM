"""Company Profile screen — Day 23.

Text search + filtered dropdown (satisfies spec's "search box + autocomplete
dropdown" and the "ticker not found" message, since a raw selectbox alone
can never produce a not-found case). KPI tiles, 10yr Revenue/Net Profit bar
chart, ROE/ROCE dual-axis line chart, pros/cons badges.
"""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from src.dashboard.utils.db import get_companies, get_pl, get_prosandcons, get_ratios

st.set_page_config(page_title="Company Profile | Nifty 100", layout="wide")

# Mirrors Day 13's Option B generic sanity bound (edge_cases.py's
# flag_implausible_ratio()). Verify against the real threshold if it differs.
ROE_ROCE_BOUND = 500.0


def fmt(val, decimals=2, suffix=""):
    """Fmt."""
    if val is None:
        return "N/A"
    try:
        if pd.isna(val):
            return "N/A"
    except TypeError:
        pass
    return f"{val:.{decimals}f}{suffix}"


def mask_if_implausible(val):
    """Mask if implausible."""
    if val is None:
        return None
    try:
        if pd.isna(val):
            return None
    except TypeError:
        return val
    if abs(val) > ROE_ROCE_BOUND:
        return None
    return val


st.header("🔍 Company Profile")

companies_df = get_companies()

# ---- Search -------------------------------------------------------------
search_term = st.text_input(
    "Search by company name or ticker",
    value="",
    placeholder="e.g. TCS or Tata Consultancy",
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
default_index = 0
if "TCS" in matches["id"].values:
    default_index = int(matches.reset_index(drop=True).query("id == 'TCS'").index[0])

selected_label = st.selectbox(
    "Select company", matches["display_label"].tolist(), index=default_index
)
selected_ticker = selected_label.split(" — ")[0]

company_row = companies_df[companies_df["id"] == selected_ticker]
if company_row.empty:
    st.warning("Ticker not found — please try another")
    st.stop()
company_row = company_row.iloc[0]

st.divider()

# ---- Company card ---------------------------------------------------------
card_left, card_right = st.columns([1, 4])
with card_left:
    logo_url = company_row.get("company_logo")
    if isinstance(logo_url, str) and logo_url.strip():
        try:
            st.image(logo_url, width=90)
        except Exception:
            pass  # 404s / broken logo URLs expected per spec — skip silently

with card_right:
    st.subheader(
        f"{company_row.get('company_name', selected_ticker)} ({selected_ticker})"
    )
    sector_line = f"{company_row.get('broad_sector', 'N/A')} · {company_row.get('sub_sector', 'N/A')}"
    st.caption(sector_line)
    about = company_row.get("about_company")
    if isinstance(about, str) and about.strip():
        st.write(about)
    else:
        st.write("No business description available.")

st.divider()

# ---- KPI tiles --------------------------------------------------------
ratios_df = get_ratios(ticker=selected_ticker)

if ratios_df.empty:
    st.warning(f"No financial_ratios data found for {selected_ticker}.")
else:
    latest = ratios_df.sort_values("year").iloc[-1]

    roe_latest = mask_if_implausible(latest.get("return_on_equity_pct"))
    roce_latest = mask_if_implausible(latest.get("return_on_capital_employed_pct"))

    c1, c2, c3 = st.columns(3)
    c1.metric("ROE", fmt(roe_latest, 1, "%"))
    c2.metric("ROCE", fmt(roce_latest, 1, "%"))
    c3.metric("Net Profit Margin", fmt(latest.get("net_profit_margin_pct"), 1, "%"))

    c4, c5, c6 = st.columns(3)
    c4.metric("D/E", fmt(latest.get("debt_to_equity"), 2, "×"))
    c5.metric("Revenue CAGR (5yr)", fmt(latest.get("revenue_cagr_5yr"), 1, "%"))
    c6.metric("FCF (latest yr, ₹Cr)", fmt(latest.get("free_cash_flow_cr"), 0))

    st.caption(f"Latest reported year: {latest.get('year', 'N/A')}")
    if roe_latest is None and latest.get("return_on_equity_pct") is not None:
        st.caption(
            f"⚠️ ROE/ROCE flagged implausible (Day 13 sanity bound, "
            f"|value| > {ROE_ROCE_BOUND:.0f}%) and shown as N/A here."
        )

st.divider()

# ---- 10-year Revenue & Net Profit bar chart --------------------------
st.subheader("Revenue & Net Profit — 10 Year History")
pl_df = get_pl(selected_ticker)
if pl_df.empty:
    st.info("No profit & loss history available for this company.")
else:
    pl_recent = pl_df.sort_values("year").tail(10)
    fig_pl = go.Figure()
    fig_pl.add_trace(go.Bar(x=pl_recent["year"], y=pl_recent["sales"], name="Revenue"))
    fig_pl.add_trace(
        go.Bar(x=pl_recent["year"], y=pl_recent["net_profit"], name="Net Profit")
    )
    fig_pl.update_layout(
        barmode="group",
        yaxis_title="₹ Crore",
        xaxis_title="Fiscal Year",
        margin=dict(t=10, b=10, l=10, r=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    st.plotly_chart(fig_pl, use_container_width=True)
    if len(pl_recent) < 10:
        st.caption(
            f"Only {len(pl_recent)} years of P&L history available for this company."
        )

st.divider()

# ---- ROE / ROCE dual-axis line chart -----------------------------------
st.subheader("ROE & ROCE — 10 Year Trend")
if ratios_df.empty:
    st.info("No ratio history available for this company.")
else:
    ratios_recent = ratios_df.sort_values("year").tail(10).copy()
    ratios_recent["roe_masked"] = ratios_recent.get(
        "return_on_equity_pct", pd.Series(dtype=float)
    ).apply(mask_if_implausible)
    ratios_recent["roce_masked"] = ratios_recent.get(
        "return_on_capital_employed_pct", pd.Series(dtype=float)
    ).apply(mask_if_implausible)

    n_masked = int(
        ratios_recent["roe_masked"].isna().sum()
        + ratios_recent["roce_masked"].isna().sum()
        - ratios_recent.get("return_on_equity_pct", pd.Series(dtype=float)).isna().sum()
        - ratios_recent.get("return_on_capital_employed_pct", pd.Series(dtype=float))
        .isna()
        .sum()
    )

    fig_roe = make_subplots(specs=[[{"secondary_y": True}]])
    fig_roe.add_trace(
        go.Scatter(
            x=ratios_recent["year"],
            y=ratios_recent["roe_masked"],
            name="ROE %",
            mode="lines+markers",
        ),
        secondary_y=False,
    )
    fig_roe.add_trace(
        go.Scatter(
            x=ratios_recent["year"],
            y=ratios_recent["roce_masked"],
            name="ROCE %",
            mode="lines+markers",
        ),
        secondary_y=True,
    )
    fig_roe.update_yaxes(title_text="ROE %", secondary_y=False)
    fig_roe.update_yaxes(title_text="ROCE %", secondary_y=True)
    fig_roe.update_xaxes(title_text="Fiscal Year")
    fig_roe.update_layout(margin=dict(t=10, b=10, l=10, r=10))
    st.plotly_chart(fig_roe, use_container_width=True)
    if n_masked > 0:
        st.caption(
            f"⚠️ {n_masked} data point(s) hidden — flagged implausible under "
            f"Day 13's sanity bound (|value| > {ROE_ROCE_BOUND:.0f}%)."
        )

st.divider()

# ---- Pros & Cons ------------------------------------------------------
st.subheader("Pros & Cons")
pc_df = get_prosandcons(selected_ticker)
if pc_df.empty:
    st.info(
        "No pros/cons data available for this company yet. Only ~8 of 92 "
        "companies have manually-sourced entries (spec Section 5.7's "
        "coverage gap) — auto-generation for the rest lands in Sprint 5."
    )
else:
    for _, row in pc_df.iterrows():
        pro_text = row.get("pros")
        con_text = row.get("cons")
        if isinstance(pro_text, str) and pro_text.strip():
            st.markdown(f"✅ {pro_text}")
        if isinstance(con_text, str) and con_text.strip():
            st.markdown(f"❌ {con_text}")
