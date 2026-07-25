"""Capital Allocation Map screen — Day 25.

Treemap of all 92 companies grouped by their 8 capital allocation patterns
(Day 11's output/capital_allocation.csv). "Click a pattern -> see company
list" is implemented as a selectbox next to the treemap rather than a
native Plotly click-event, since streamlit-plotly-events isn't a confirmed
project dependency — this is a documented interpretation of the spec's
"clicking a pattern shows company list" requirement, functionally
equivalent without adding a new package mid-sprint.
"""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import plotly.express as px
import streamlit as st

from src.dashboard.utils.db import get_capital_allocation, get_companies

st.set_page_config(page_title="Capital Allocation | Nifty 100", layout="wide")

st.header("🗺️ Capital Allocation Map")

alloc_df = get_capital_allocation()
companies_df = get_companies()

if alloc_df.empty:
    st.warning(
        "output/capital_allocation.csv not found or empty — re-run Day 11's "
        "generate_capital_allocation.py."
    )
    st.stop()

expected_cols = {"company_id", "year", "pattern_label"}
missing_cols = expected_cols - set(alloc_df.columns)
if missing_cols:
    st.error(
        f"capital_allocation.csv is missing expected column(s): {missing_cols}. "
        "Check Day 11's generate_capital_allocation.py output schema."
    )
    st.stop()

# Latest year per company (avoids a treemap double-counting a company
# across multiple historical years).
latest_idx = alloc_df.groupby("company_id")["year"].idxmax()
latest_alloc = alloc_df.loc[latest_idx].reset_index(drop=True)

latest_alloc = latest_alloc.merge(
    companies_df[["id", "company_name", "broad_sector"]],
    left_on="company_id",
    right_on="id",
    how="left",
)

st.subheader("92 Companies by Capital Allocation Pattern (Latest Year)")
pattern_counts = latest_alloc.groupby("pattern_label").size().reset_index(name="count")

fig_tree = px.treemap(
    latest_alloc,
    path=[px.Constant("All Companies"), "pattern_label", "company_id"],
    values=None,  # equal-weight leaves; pattern size reflects company count
)
fig_tree.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=550)
st.plotly_chart(fig_tree, use_container_width=True)

st.caption(
    f"{len(latest_alloc)} of 92 companies have a capital allocation pattern "
    f"assigned for their latest year. {len(pattern_counts)} distinct pattern(s) present."
)

st.divider()

st.subheader("Drill Down: Companies in a Pattern")
pattern_options = sorted(latest_alloc["pattern_label"].dropna().unique())
if not pattern_options:
    st.info("No pattern labels available to drill into.")
else:
    selected_pattern = st.selectbox(
        "Select a pattern to see its companies", pattern_options
    )
    drill_df = latest_alloc[latest_alloc["pattern_label"] == selected_pattern][
        ["company_id", "company_name", "broad_sector", "year"]
    ].sort_values("company_id")
    st.write(f"**{len(drill_df)} companies** in pattern **{selected_pattern}**:")
    st.dataframe(drill_df, use_container_width=True, hide_index=True)
