"""Annual Reports screen — Day 25.

Company search -> list of available annual report years with clickable
BSE PDF links. Live 404 checking (spec's requests.head() validation) is
opt-in via a button rather than automatic on page load — DQ-13 in
validator.py already treats this same check as slow/opt-in against 1,585
real URLs (skip_url_check=True is validator.py's own default), so the
dashboard follows the identical caution rather than blocking page load
on ~15 sequential HTTP requests per company.
"""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import requests
import streamlit as st

from src.dashboard.utils.db import get_companies, get_documents

st.set_page_config(page_title="Annual Reports | Nifty 100", layout="wide")

st.header("📄 Annual Reports")

companies_df = get_companies()

search_term = st.text_input("Search by company name or ticker", placeholder="e.g. ABB")
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

docs_df = get_documents(selected_ticker)

if docs_df.empty:
    st.info(
        f"No annual report links found for {selected_ticker}. "
        "Spec's documents coverage is ~75/92 companies (82%) — some gaps expected."
    )
    st.stop()

check_live = st.checkbox(
    "Check link availability now (slower — sends a live HTTP request per year)",
    value=False,
)

st.write(f"**{len(docs_df)} annual report year(s)** on file for {selected_ticker}:")

docs_sorted = docs_df.sort_values("report_year", ascending=False)

for _, row in docs_sorted.iterrows():
    year = row.get("report_year")
    url = row.get("annual_report_url")

    col_year, col_link, col_status = st.columns([1, 4, 2])
    col_year.write(f"**{year}**")

    if not isinstance(url, str) or not url.strip():
        col_link.write("—")
        col_status.markdown(":red[Report unavailable]")
        continue

    col_link.markdown(f"[{url}]({url})")

    if check_live:
        try:
            resp = requests.head(url, timeout=4, allow_redirects=True)
            if resp.status_code == 200:
                col_status.markdown(":green[Available]")
            else:
                col_status.markdown(f":red[Report unavailable ({resp.status_code})]")
        except requests.RequestException:
            col_status.markdown(":red[Report unavailable (no response)]")
    else:
        col_status.write("—")

st.caption(
    "Link decay is expected over time (spec Risk R-02) — the dashboard shows "
    "'Report unavailable' gracefully rather than failing the page."
)
