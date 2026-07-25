"""Nifty 100 Financial Intelligence Platform — Streamlit entry point.
Run with: streamlit run src/dashboard/app.py  (from the project root)
"""

import sys
from pathlib import Path

# app.py is at src/dashboard/app.py -> parents[2] is the project root.
# Needed because `streamlit run` puts the script's own folder on sys.path[0],
# not the project root — same gotcha documented for screener_export.py (Day 17)
# and peer.py (Day 18). Without this, `from src...` imports fail.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st

st.set_page_config(
    page_title="Nifty 100 Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("📊 Nifty 100 Financial Intelligence Platform")
st.markdown("""
Use the sidebar to navigate between the 8 screens:

1. **Home** — portfolio-wide summary KPIs and sector breakdown
2. **Company Profile** — search any of the 92 companies for a full financial card
3. **Screener** — multi-metric filters with live results and CSV export
4. **Peer Comparison** — radar chart vs peer group average
5. **Trend Analysis** — multi-year, multi-metric overlay charts
6. **Sector Analysis** — sector bubble chart and median KPI comparison
7. **Capital Allocation Map** — treemap of the 8 capital allocation patterns
8. **Annual Reports** — BSE annual report link repository

Data is read live from `data/nifty100.db` and cached for 10 minutes per query.
""")

from src.dashboard.utils.db import get_companies  # noqa: E402

st.divider()
st.subheader("Database connection check")
try:
    companies_df = get_companies()
    st.success(f"Connected — {len(companies_df)} companies loaded from nifty100.db.")
    if len(companies_df) != 92:
        st.warning(
            f"Expected 92 companies (AC-01), got {len(companies_df)}. "
            "Check data/nifty100.db was built with the full Sprint 1 load."
        )
except Exception as exc:
    st.error(f"Could not read the database: {exc}")
