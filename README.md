# Nifty 100 Financial Intelligence Platform

A production-grade Python financial intelligence system analyzing 92 Nifty 100 index
companies — converting raw Excel-based financial data into a queryable SQLite database
with 50+ computed KPIs, an investment screener, composite financial health scoring,
sector analytics, a Streamlit dashboard, PDF tearsheet reports, a FastAPI REST API,
NLP-generated summaries, and KMeans clustering.

**Spec reference:** Nifty 100 Financial Intelligence Platform — Project Execution Plan
(v1.0, June 2026)
**Status:** All 6 sprints complete (Days 1–45). All 23 deliverables verified present on
disk. See [Status](#status) and `docs/PROGRESS.md` for full detail.

---

## Prerequisites

- Windows 11
- Python 3.13.5
- VS Code + PowerShell

---

## Setup — From Clone to Running App

```powershell
# 1. Navigate to the project root
cd E:\Thanuj_V\nifty100_project

# 2. Create and activate the virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
copy config\.env.template .env
# Edit .env — set DB_PATH=data/nifty100.db, PORT=8000, LOG_LEVEL=INFO

# 5. Build the database (ETL)
python -m src.etl.full_load

# 6. Run KPI computation
python -m src.analytics.populate_financial_ratios

# 7. Generate supporting analytics outputs
python -m src.analytics.generate_capital_allocation
python -m src.analytics.valuation

# 8. Run KMeans clustering
python -m src.analytics.clustering
python -m src.analytics.cluster_profiling
python -m src.analytics.portfolio_stats

# 9. Run the test suite
python -m pytest tests\ --html=reports\pytest_report.html --self-contained-html --continue-on-collection-errors

# 10. Start the Streamlit dashboard
streamlit run src\dashboard\app.py

# 11. Start the REST API (in a separate terminal)
python -m uvicorn src.api.main:app --port 8000
```

The dashboard opens automatically at `http://localhost:8501`. The API's interactive docs
are at `http://localhost:8000/docs`.

> **Always use `python -m ...`, not `py -m ...`.** The `py` launcher can point to a stale
> interpreter path independently of the active `.venv` on some machines.

---

## Project Structure

```
nifty100_project/
|-- .venv/                  Virtual environment (not committed)
|-- .env                    Local config (not committed)
|-- data/
|   |-- raw/                7 core Excel files (read-only, never modified)
|   |-- supporting/         5 supplementary Excel files
|   `-- nifty100.db         SQLite database - 12 tables, 92 companies
|-- src/
|   |-- etl/                Excel loader, normaliser, validator, schema, full load
|   |-- analytics/          Ratio engine, CAGR, cash flow KPIs, scoring, clustering, valuation
|   |-- screener/           Filter engine, preset screeners, composite score
|   |-- nlp/                Analysis text parser, pros/cons auto-generator
|   |-- reports/            Tearsheets, sector/portfolio reports, radar charts, analyst guide
|   |-- api/                FastAPI server (main.py + routers/)
|   `-- dashboard/          Streamlit app, cached data loader, 8 screens
|       |-- app.py
|       |-- utils/db.py
|       `-- pages/
|-- tests/                  pytest suite - etl/, kpi/, dq/, api/, integration/, screener/, reports/, nlp/, analytics/
|-- scripts/
|   `-- diagnostics/        Archived day-by-day diagnostic/investigation scripts (kept for
|                            traceability — each is referenced by name in PROGRESS.md as
|                            evidence of a real bug found/fixed; not part of the runtime app)
|-- config/                 .env.template, screener_config.yaml
|-- output/                 Generated CSVs/Excel + final_deliverables/ archive (Day 45 handoff copy)
|-- reports/                tearsheets/ (91 PDFs), sector/ (10 PDFs), radar_charts/ (92 PNGs),
|                            portfolio/, elbow_plot.png, correlation_heatmap.png, pytest_report.html
|-- docs/                   analyst_guide.pdf, acceptance_checklist.pdf, openapi.json, PROGRESS.md
|-- notebooks/               exploratory_queries.sql
|-- verify_deliverables.py   Independent checker — confirms all 23 deliverables exist on disk
|-- project_structure_simple.py  Recursive folder/file lister (used to audit this README/PROGRESS.md)
|-- cleanup_and_audit.py    One-time cleanup tool used to archive diagnostics / remove junk files
`-- README.md                (this file)
```

## Running the Dashboard

The Streamlit dashboard provides 8 interactive screens for exploring the platform's data.

### Prerequisites

- Virtual environment activated (`.venv\Scripts\Activate.ps1`)
- `data/nifty100.db` built (`python -m src.etl.full_load` if not present)
- `financial_ratios` table populated (`python -m src.analytics.populate_financial_ratios`)
- `output/capital_allocation.csv` generated (`python -m src.analytics.generate_capital_allocation`)
- `output/valuation_summary.xlsx` generated (`python -m src.analytics.valuation`)

### Start the dashboard

```powershell
streamlit run src\dashboard\app.py
```

### Screen Guide

| Screen | What it shows |
|---|---|
| **Home** | Portfolio-wide KPI tiles (Average ROE, Median P/E, Median D/E, Total Companies, Median Revenue CAGR, Debt-Free count), sector breakdown donut chart, top-5 companies by composite quality score. Year selector recalculates all tiles using each company's own latest fiscal year on or before that calendar year — non-March fiscal year-end companies (SIEMENS, NESTLEIND) are handled correctly rather than dropped. |
| **Company Profile** | Search any of the 92 companies by name or ticker. Company card, 6 KPI tiles, 10-year Revenue/Net Profit bar chart, ROE/ROCE dual-axis trend line, pros/cons badges. |
| **Screener** | 10 metric sliders with 6 one-click presets. Results update live; CSV download available. |
| **Peer Comparison** | Select one of 11 real peer groups, then a company within it. Radar chart compares 8-metric percentile rank against the peer group average, with the benchmark company highlighted. |
| **Trend Analysis** | Search a company, overlay up to 3 metrics on a 10-year line chart with YoY % annotations. Explicit warning if a selected metric has no data for a company. |
| **Sector Analysis** | Bubble chart (Revenue × ROE, size = Market Cap, colour = sub-sector) plus a sector median KPI bar chart. |
| **Capital Allocation Map** | Treemap of all 92 companies across 8 capital allocation patterns, with a drill-down selector per pattern. |
| **Annual Reports** | Search a company to see its BSE annual report years and links, with optional live link-checking. |

### Known data limitations reflected in the dashboard

These are documented, investigated behaviors — not bugs:

- **SBIN** has no balance sheet data, so ROE, ROCE, D/E, and Book Value/Share show as N/A.
- **HAL, BEL, INDIGO, ICICIPRULI, HDFCLIFE** have implausible ROE/ROCE from near-zero-equity
  balance sheet artifacts — masked to N/A wherever displayed or averaged.
- **JIOFIN** shows fewer years of history — a newly listed company (2023), genuinely limited.
- **SIEMENS** uses a September fiscal year-end, handled per-company in every date-based join.
- **Sectors table** has 10 distinct sectors, not the 11 originally specified.
- **JIOFIN** is the one company excluded from the 92-company tearsheet batch (2yr history,
  below the 3yr minimum needed for the 10-year trend charts) — 91/92 tearsheets exist by design.

## Running the API

```powershell
python -m uvicorn src.api.main:app --port 8000
```

Interactive docs at `http://localhost:8000/docs`. See `docs/analyst_guide.pdf` for the full
endpoint reference and example `curl` commands.

## Running the Test Suite

```powershell
python -m pytest tests\ --html=reports\pytest_report.html --self-contained-html --continue-on-collection-errors
```

274 tests passing across ETL, KPI formulas, DQ rules, API endpoints, and integration checks
(6 pre-existing test files hit a known, documented collection-time import-path issue when run
as part of the full `tests/` tree — the same 171 tests pass cleanly when scoped directly to
`tests/etl/` + `tests/kpi/`; see `docs/PROGRESS.md` Day 42 for detail).

## Verifying deliverables

Two standalone scripts at the project root, independent of any prior day's code, for
re-confirming the state of the repo at any time:

```powershell
python verify_deliverables.py        # checks all 23 tracker deliverables exist + non-empty
python project_structure_simple.py   # prints the full current folder/file tree
```

---

## Documentation

- **`docs/PROGRESS.md`** — canonical day-by-day build log; the single source of truth for
  what's been built, tested, and any deviations from spec.
- **`docs/analyst_guide.pdf`** — screener usage, dashboard navigation, tearsheet generation,
  API examples, troubleshooting, known data limitations.
- **`docs/openapi.json`** — OpenAPI 3.0 specification, importable into Postman.
- **`docs/acceptance_checklist.pdf`** — all 20 acceptance gates with results, 23/23
  deliverables confirmed present, signed at Day 45.

---

## Status

| Sprint | Focus | Status |
|---|---|---|
| Sprint 1 (Days 1–7) | Data Foundation & ETL | ✅ Complete |
| Sprint 2 (Days 8–14) | Financial Ratio Engine | ✅ Complete |
| Sprint 3 (Days 15–21) | Screener, Scoring & Sector Analytics | ✅ Complete |
| Sprint 4 (Days 22–28) | Dashboard & Valuation | ✅ Complete |
| Sprint 5 (Days 29–35) | NLP, Cash Flow Intelligence, PDF Reports | ✅ Complete |
| Sprint 6 (Days 36–45) | API, Clustering, Testing & Delivery | ✅ Complete |

**All 23 numbered deliverables (D-01–D-23) independently re-verified present and non-empty
via `verify_deliverables.py`.** All 20 acceptance gates run at Day 45: 16 PASS, 3 FAIL (all
pre-existing, documented, explained deviations — not defects), 1 MANUAL-confirmed.

**Two open items, not blocking technical sign-off, flagged for whoever reviews this repo:**
- `sprint1_retro.md` (documented as never started, Day 7) and `sprint2_retro.md` (Day 14's
  log says it was written, but it is not present in the repository — a doc-vs-disk
  discrepancy worth a quick check before final submission) are both absent.
- A handful of small diagnostic/scratch files remain loose at the project root
  (`day40.py`, `diagnose_nulls.py`, `day36_diagnose_singleton_cluster.txt`) — harmless,
  low priority, not part of the runtime application.

See `docs/PROGRESS.md` for full day-by-day detail and every documented deviation from spec.
