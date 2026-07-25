"""Financial Screener screen — Day 24.

10 metric sliders, 6 preset buttons, live-filtering results table, CSV
download, result count label. ROE/ROCE are masked under Day 13's sanity
bound before filtering/display (HAL/BEL/INDIGO/ICICIPRULI/HDFCLIFE-style
implausible values must not silently qualify or disqualify a company).
ICR follows Day 15's redefinition: a null ICR with real debt outstanding
fails a min-ICR filter; a null ICR with zero debt (genuinely debt-free)
passes regardless of the slider.
"""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import pandas as pd
import streamlit as st

from src.dashboard.utils.db import get_companies, get_latest_ratios, get_valuation

st.set_page_config(page_title="Screener | Nifty 100", layout="wide")

ROE_ROCE_BOUND = 500.0  # mirrors Day 13's edge_cases.py sanity bound


def find_col(df: pd.DataFrame, candidates: list) -> str | None:
    """Find col."""
    for c in candidates:
        if c in df.columns:
            return c
    return None


st.header("🎯 Financial Screener")

# ---- Load & merge universe ------------------------------------------------
ratios_df = get_latest_ratios()
companies_df = get_companies()
valuation_df = get_valuation()

if ratios_df.empty:
    st.error(
        "financial_ratios table is empty — check Sprint 2's populate_financial_ratios.py has been run."
    )
    st.stop()

# Latest valuation row per company (market_cap has 2019-2024 annual rows)
if not valuation_df.empty:
    val_latest = (
        valuation_df.sort_values("year").groupby("company_id", as_index=False).tail(1)
    )
else:
    val_latest = pd.DataFrame(columns=["company_id"])

universe = ratios_df.merge(
    companies_df[["id", "company_name", "broad_sector"]],
    left_on="company_id",
    right_on="id",
    how="left",
).merge(val_latest, on="company_id", how="left", suffixes=("", "_val"))

# ---- Resolve real column names ------------------------------------------
col_roe = find_col(universe, ["return_on_equity_pct"])
col_roce = find_col(universe, ["return_on_capital_employed_pct"])
col_npm = find_col(universe, ["net_profit_margin_pct"])
col_opm = find_col(universe, ["operating_profit_margin_pct"])
col_de = find_col(universe, ["debt_to_equity"])
col_fcf = find_col(universe, ["free_cash_flow_cr"])
col_rev_cagr = find_col(universe, ["revenue_cagr_5yr"])
col_pat_cagr = find_col(universe, ["pat_cagr_5yr"])
col_icr = find_col(universe, ["interest_coverage", "interest_coverage_ratio"])
col_total_debt = find_col(universe, ["total_debt_cr"])
col_composite = find_col(
    universe, ["composite_score_sector_relative", "composite_quality_score"]
)
col_pe = find_col(universe, ["pe_ratio"])
col_pb = find_col(universe, ["pb_ratio"])
col_div_yield = find_col(universe, ["dividend_yield_pct"])

# Mask implausible ROE/ROCE (Day 13) before anything downstream uses them
if col_roe:
    universe[col_roe] = universe[col_roe].where(
        universe[col_roe].abs() <= ROE_ROCE_BOUND
    )
if col_roce:
    universe[col_roce] = universe[col_roce].where(
        universe[col_roce].abs() <= ROE_ROCE_BOUND
    )

missing_cols = [
    name
    for name, col in [
        ("ROE", col_roe),
        ("ROCE", col_roce),
        ("NPM", col_npm),
        ("OPM", col_opm),
        ("D/E", col_de),
        ("FCF", col_fcf),
        ("Revenue CAGR 5yr", col_rev_cagr),
        ("PAT CAGR 5yr", col_pat_cagr),
        ("ICR", col_icr),
        ("P/E", col_pe),
        ("P/B", col_pb),
        ("Dividend Yield", col_div_yield),
    ]
    if col is None
]
if missing_cols:
    st.warning(
        f"Columns not found for: {', '.join(missing_cols)} — those filters "
        "are disabled below rather than crashing the screen."
    )

# ---- Session-state slider defaults ("off" = non-restrictive) ------------
DEFAULTS = {
    "roe_min": -50.0,
    "de_max": 10.0,
    "fcf_min": -50000.0,
    "rev_cagr_min": -30.0,
    "pat_cagr_min": -30.0,
    "opm_min": -30.0,
    "pe_max": 200.0,
    "pb_max": 50.0,
    "div_yield_min": 0.0,
    "icr_min": 0.0,
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v
if "exclude_financials_de" not in st.session_state:
    st.session_state["exclude_financials_de"] = True  # D/E carve-out, Day 16 convention

PRESETS = {
    "Quality Compounder": {
        "roe_min": 15.0,
        "de_max": 1.0,
        "fcf_min": 0.0,
        "rev_cagr_min": 10.0,
        "caption": "Maps ROE>15%, D/E<1, FCF>0, Rev CAGR 5yr>10% exactly (Day 16, 21/92 companies).",
    },
    "Value Pick": {
        "pe_max": 50.0,
        "pb_max": 5.0,
        "de_max": 2.0,
        "div_yield_min": 1.0,
        "caption": "Recalibrated P/E<50, P/B<5.0 (Day 16 — spec's P/E<20 returned only 2 companies).",
    },
    "Growth Accelerator": {
        "pat_cagr_min": 20.0,
        "rev_cagr_min": 15.0,
        "de_max": 2.0,
        "caption": "PAT CAGR 5yr>20%, Revenue CAGR 5yr>15%, D/E<2.0 — exact spec thresholds.",
    },
    "Dividend Champion": {
        "div_yield_min": 3.5,
        "fcf_min": 0.0,
        "caption": "Recalibrated yield>3.5% (Day 16). Payout<80% not representable by these sliders — omitted here.",
    },
    "Debt-Free Blue Chip": {
        "de_max": 0.1,
        "roe_min": 12.0,
        "force_exclude_financials": True,
        "caption": "D/E<0.1, ROE>12%, Financials sector excluded (Day 16). Revenue>5,000 Cr floor not representable — omitted here.",
    },
    "Turnaround Watch": {
        "rev_cagr_min": 18.0,
        "caption": "Approximated using the 5yr Revenue CAGR slider at Day 16's recalibrated 18% cutoff — the real preset uses 3yr CAGR (computed on the fly, not in this slider set) plus FCF-improving and D/E-declining trend checks not representable by static sliders.",
    },
}

st.subheader("Preset Screeners")
preset_cols = st.columns(6)
for i, (name, cfg) in enumerate(PRESETS.items()):
    if preset_cols[i].button(name, use_container_width=True):
        for k, v in DEFAULTS.items():
            st.session_state[k] = v
        for k, v in cfg.items():
            if k in DEFAULTS:
                st.session_state[k] = v
        if cfg.get("force_exclude_financials"):
            st.session_state["exclude_financials_de"] = True
        st.session_state["_active_preset_caption"] = cfg["caption"]
        st.rerun()

if "_active_preset_caption" in st.session_state:
    st.caption(f"ℹ️ {st.session_state['_active_preset_caption']}")

st.divider()

# ---- Sidebar sliders --------------------------------------------------
st.sidebar.subheader("Screener Filters")
roe_min = st.sidebar.slider(
    "ROE min (%)", -50.0, 100.0, key="roe_min", step=1.0, disabled=col_roe is None
)
de_max = st.sidebar.slider(
    "D/E max", 0.0, 10.0, key="de_max", step=0.1, disabled=col_de is None
)
fcf_min = st.sidebar.slider(
    "FCF min (₹Cr)",
    -50000.0,
    150000.0,
    key="fcf_min",
    step=1000.0,
    disabled=col_fcf is None,
)
rev_cagr_min = st.sidebar.slider(
    "Revenue CAGR 5yr min (%)",
    -30.0,
    60.0,
    key="rev_cagr_min",
    step=1.0,
    disabled=col_rev_cagr is None,
)
pat_cagr_min = st.sidebar.slider(
    "PAT CAGR 5yr min (%)",
    -30.0,
    80.0,
    key="pat_cagr_min",
    step=1.0,
    disabled=col_pat_cagr is None,
)
opm_min = st.sidebar.slider(
    "OPM min (%)", -30.0, 60.0, key="opm_min", step=1.0, disabled=col_opm is None
)
pe_max = st.sidebar.slider(
    "P/E max", 0.0, 200.0, key="pe_max", step=1.0, disabled=col_pe is None
)
pb_max = st.sidebar.slider(
    "P/B max", 0.0, 50.0, key="pb_max", step=0.5, disabled=col_pb is None
)
div_yield_min = st.sidebar.slider(
    "Dividend Yield min (%)",
    0.0,
    10.0,
    key="div_yield_min",
    step=0.1,
    disabled=col_div_yield is None,
)
icr_min = st.sidebar.slider(
    "ICR min", 0.0, 50.0, key="icr_min", step=0.5, disabled=col_icr is None
)
exclude_fin_de = st.sidebar.checkbox(
    "Apply Financials D/E carve-out (Day 16 convention)",
    key="exclude_financials_de",
)

# ---- Apply filters ------------------------------------------------------
mask = pd.Series(True, index=universe.index)
is_financials = universe["broad_sector"] == "Financials"

if col_roe and roe_min > DEFAULTS["roe_min"]:
    mask &= universe[col_roe].fillna(-9999) >= roe_min
if col_de and de_max < DEFAULTS["de_max"]:
    de_mask = universe[col_de].fillna(9999) <= de_max
    if exclude_fin_de:
        de_mask = de_mask | is_financials
    mask &= de_mask
if col_fcf and fcf_min > DEFAULTS["fcf_min"]:
    mask &= universe[col_fcf].fillna(-1e12) >= fcf_min
if col_rev_cagr and rev_cagr_min > DEFAULTS["rev_cagr_min"]:
    mask &= universe[col_rev_cagr].fillna(-9999) >= rev_cagr_min
if col_pat_cagr and pat_cagr_min > DEFAULTS["pat_cagr_min"]:
    mask &= universe[col_pat_cagr].fillna(-9999) >= pat_cagr_min
if col_opm and opm_min > DEFAULTS["opm_min"]:
    mask &= universe[col_opm].fillna(-9999) >= opm_min
if col_pe and pe_max < DEFAULTS["pe_max"]:
    mask &= universe[col_pe].fillna(9999) <= pe_max
if col_pb and pb_max < DEFAULTS["pb_max"]:
    mask &= universe[col_pb].fillna(9999) <= pb_max
if col_div_yield and div_yield_min > DEFAULTS["div_yield_min"]:
    mask &= universe[col_div_yield].fillna(-1) >= div_yield_min
if col_icr and icr_min > DEFAULTS["icr_min"]:
    debt_free = (
        (universe[col_total_debt] == 0)
        if col_total_debt
        else pd.Series(False, index=universe.index)
    )
    icr_ok = universe[col_icr].fillna(-1) >= icr_min
    mask &= icr_ok | debt_free

results = universe[mask].copy()

# ---- Result count + table ----------------------------------------------
st.markdown(f"**{len(results)} companies match your filters**")

display_candidates = [
    "company_id",
    "company_name",
    "broad_sector",
    col_composite,
    col_roe,
    col_roce,
    col_npm,
    col_de,
    col_fcf,
    col_rev_cagr,
    col_pat_cagr,
    col_pe,
    col_pb,
    col_div_yield,
]
display_cols = [c for c in display_candidates if c is not None]
display_df = results[display_cols].copy()
sort_col = col_composite if col_composite else "company_id"
display_df = display_df.sort_values(sort_col, ascending=False, na_position="last")
display_df.columns = [
    c.replace("_pct", " %").replace("_", " ").title() for c in display_df.columns
]

st.dataframe(display_df, use_container_width=True, hide_index=True)

# ---- CSV download ---------------------------------------------------------
csv_bytes = display_df.to_csv(index=False).encode("utf-8")
st.download_button(
    "⬇️ Download results as CSV",
    data=csv_bytes,
    file_name="screener_results.csv",
    mime="text/csv",
    disabled=display_df.empty,
)
