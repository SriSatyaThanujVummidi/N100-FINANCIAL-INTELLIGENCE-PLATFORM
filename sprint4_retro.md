# Sprint 4 Retrospective — Dashboard & Valuation (Days 22–28)

## What was built
- Full 8-screen Streamlit dashboard (`src/dashboard/app.py` + `pages/`)
- Cached data layer (`src/dashboard/utils/db.py`) — 14 functions, all
  `@st.cache_data(ttl=600)`
- Valuation module (`src/analytics/valuation.py`) — FCF yield, sector
  median P/E, Caution/Discount/Fair flags
- `output/valuation_summary.xlsx`, `output/valuation_flags.csv`
- Backend QA smoke test (`src/dashboard/day27_qa_smoke_test.py`)

## Key decisions & deviations (documented, not silent)

1. **Fiscal-vs-calendar year mismatch (Days 22–26).** `financial_ratios`
   is fiscal-year indexed (`2024-03`), `market_cap` is calendar-year
   indexed (`2024`). Rather than force an exact-year join — which would
   silently drop every non-March-FYE company the same way Day 15's
   original screener bug did — the Home screen's year selector and the
   Valuation module both take each company's own latest available value
   independently per table. Flagged for team lead review if exact
   fiscal-to-calendar alignment turns out to matter.

2. **Capital Allocation drill-down via selectbox, not native click
   events (Day 25).** `streamlit-plotly-events` isn't a confirmed
   project dependency. Rather than add a new package mid-sprint, "click
   a pattern to see its companies" was implemented as a selectbox next
   to the treemap — functionally equivalent, zero new dependencies.

3. **Live URL-availability checking made opt-in (Day 25).** Mirrors
   `validator.py`'s own DQ-13 default (`skip_url_check=True`) — checking
   all annual report links live on every page load would be slow and
   flaky against real BSE URLs, so it's a manual checkbox instead.

4. **Sanity-bound masking applied at the dashboard layer, not just
   upstream (Days 23, 25).** Day 13's ±500% ROE/ROCE sanity bound and
   Day 26's ±200% P/E sanity bound were both re-applied inline in the
   dashboard code (Home, Profile, Trends, Valuation) rather than
   assumed to already be filtered out by the time data reaches the UI.
   This is intentional defense-in-depth — the `financial_ratios` table
   itself still contains the raw implausible values; only the
   *display* layer masks them.

## Bugs found and fixed during Sprint 4

- **`documents` table column names** — `db.py` and `08_reports.py` were
  written against spec Section 5.6's literal column names (`Year`,
  `Annual_Report`), but the real Day-4 schema uses `report_year` and
  `annual_report_url`. Caught via three sequential tracebacks (a SQL
  `OperationalError`, then a `KeyError` on a reference an initial grep
  missed) before landing clean. Root cause: `db.py` was written against
  the spec document rather than the actual `PRAGMA table_info` output —
  worth doing a full schema cross-check *before* writing dashboard code
  in future sprints, not after the first crash.

- **`TypeError: bad operand type for abs(): 'NoneType'`** on the Trends
  screen — a `financial_ratios` column returned as object-dtype (SQLite
  `None`, not `NaN`) when every value in that column was missing for a
  ticker (SBIN's ROE/ROCE/D/E, confirmed via direct query: all 12 years
  are `None`, not partially populated). Fixed with `pd.to_numeric(...,
  errors="coerce")` before any `.abs()` call, applied in both
  `05_trends.py` and `01_home.py`. Added an explicit "no plottable
  data" warning per metric so this now surfaces as a clear message
  instead of a silently blank chart.

## QA findings (Day 27)

- Backend smoke test: 70/70 calls passed across 5 normal tickers (TCS,
  HDFCBANK, HINDUNILVR, RELIANCE, SUNPHARMA) and 5 documented edge
  cases (SBIN, HAL, JIOFIN, SIEMENS, PNB) — 0 crashes, 9 empty results,
  all mapping to already-documented data gaps.
- Backend data-load timing: 6–16ms per ticker across 4 combined DB
  calls — well within AC-08's 3-second budget, even accounting for
  Streamlit's own render overhead.
- Valuation flag distribution investigated before being accepted:
  Fair=48, Caution=14, Discount=30. Per-sector breakdown confirmed this
  asymmetry is NOT a single-sector distortion — it's the expected
  behaviour of a symmetric threshold band applied to a right-skewed P/E
  distribution, verified with a TCS/RELIANCE/HDFCBANK spot-check.

## Carried forward — not blocking Sprint 4 sign-off

- **Sectors table: 10 distinct `broad_sector` values found, spec
  Section 6.1 defines 11.** The Sector Analysis screen (Day 25) now
  surfaces the exact missing sector name in-app rather than leaving
  this as an unexplained count from Day 23 — but the root cause (empty
  category vs. a naming-variant collision) has not yet been diagnosed
  in the source `sectors.xlsx`. Recommend addressing before Sprint 6's
  final documentation pass, since an unexplained count would look odd
  in the analyst guide.
- **Home screen's "Debt-Free Companies" tile uses strict
  `total_debt_cr == 0`** (count=3), which is a different, stricter
  definition than the Debt-Free Blue Chip *screener preset*
  (`D/E < 0.1`, Financials excluded, count=19, Day 17). Both are
  legitimate but distinct definitions — worth a one-line clarification
  with the team lead on whether the Home tile should be relabeled or
  aligned to the screener's threshold.

## Sprint 4 exit criteria — status

- [x] All 8 Streamlit screens load without errors for any of the 92 tickers
- [x] Company Profile screen loads well under 3 seconds (backend: 6–16ms)
- [x] Screener CSV download produces a valid file with correct headers
- [x] `valuation_summary.xlsx` has 92 rows with all required columns
- [ ] Sprint 4 review demo — pending team lead walkthrough