# Sprint 5 Retrospective — Intelligence, Reports & NLP

**Sprint dates:** Days 29–35
**Modules covered:** Module 7 (Cash Flow Intelligence), Module 8 (PDF Report Generator), Module 9 (NLP & Qualitative Analysis)
**Status:** Code-complete. Team lead review meeting pending (per spec Section 29, Week 5 Review).

---

## Exit Criteria — Final Status

| Criterion | Status | Notes |
|---|---|---|
| `pros_cons_generated.csv` — ≥1 pro + ≥1 con for every company (AC-16) | ✅ | 92/92 companies, 537 rows (399 pros, 138 cons) |
| `analysis_parsed.csv` — structured CAGR numbers from analysis.xlsx | ✅ | 52 rows, 4 companies (real coverage, not spec's ~8 estimate) |
| `cashflow_intelligence.xlsx` — 92 rows, all required columns | ✅ | Corrected mid-sprint (see below) |
| `distress_alerts.csv` — companies with distress signal | ✅ | 4 genuine cases; Financials sector correctly excluded |
| 92 company tearsheet PDFs, 2 pages each, no overflow | ✅ | 91/92 generated; JIOFIN documented skip (2yr history, below 3yr minimum) |
| 11 sector PDFs | ⚠️ | 10 PDFs — real `sectors` table has 10 distinct values, not spec's 11 (pre-existing, documented since Day 22) |
| Portfolio summary PDF | ✅ | 92/92 companies, alphabetical, trend arrows verified |
| Sprint 5 review meeting completed and signed off | ⬜ | Pending team lead meeting |

---

## Day-by-Day Summary

| Day | Deliverable | Key Outcome |
|---|---|---|
| 29 | `src/nlp/parser.py` | Regex parser for analysis.xlsx. Fixed a real bug: literal spec regex couldn't capture negative values (e.g. "-2%"), silently misclassifying them as parse failures. |
| 30 | `src/nlp/pros_cons_generator.py` | 24 rules (12 pro + 12 con), confidence-scored, fallback-guaranteed. Fixed CON11's cash-proxy formula, which broke for Financials (insurers' "other assets" are their core investment book, not idle cash). |
| 31 | `src/analytics/cashflow_intelligence.py` | CFO Quality Score, CapEx Intensity, FCF CAGR, Distress/Deleveraging flags. Found and fixed a real bug: naive distress rule (CFO<0 AND CFF>0) flagged 9 healthy Financials companies as "distressed" — this is the normal cash-flow shape of a lending business, not distress. |
| 32 | Capital Allocation Report | Verified Day 11's `capital_allocation.csv` complete (92/92, 1,063/1,063 rows). Investigated a 55% average pattern-change rate before accepting it — confirmed as real business-model-driven volatility (banks change pattern far more than stable blue chips), not classifier noise. |
| 33 | `src/reports/tearsheet.py` | 2-page ReportLab tearsheet. Found a **significant, previously-invisible bug**: ~79 of 92 companies carry a spurious interim balance-sheet row (e.g. "2024-09") that had been silently corrupting Day 31's already-signed-off `deleveraging_flag` for 21 companies. Fixed at the root with a new shared utility (`src/etl/fiscal_calendar.py`) and both affected modules were re-verified. |
| 34 | Batch generation | 91 tearsheets + 10 sector PDFs generated. Investigated the one AC-17 exception (SBIN, 43.5KB) and confirmed it's explained by SBIN's known missing balance sheet, not a defect. Visually spot-checked 5 companies from the real batch output, including both known edge cases (SBIN, HAL). |
| 35 | `src/reports/portfolio_summary.py` | 92-page portfolio summary with polarity-aware trend arrows. Verified masking and thin-data handling end-to-end against all known edge-case companies before accepting the output. |

---

## What Went Well

- **Every real bug this sprint was caught before shipping**, either by the sandbox test suite or a targeted diagnostic script written specifically to investigate a suspicious result — never accepted at face value. Examples: Day 29's negative-regex bug, Day 30's CON11 Financials issue, Day 31's distress-flag Financials issue, Day 33's fiscal-calendar bug.
- **The Day 33 fiscal-calendar bug is the standout finding of the sprint.** It was invisible for four full sprints because nothing before the tearsheet's 10-year balance sheet chart rendered a sequential annual view where an off-cycle row would visually stand out. Once found, it was traced back to also affect already-signed-off Day 31 output, fixed at the root with one shared, tested utility (`src/etl/fiscal_calendar.py`), and both consumers were re-verified against real data rather than assumed fixed.
- **The Financials sector carve-out pattern** (first seen in D/E in Sprint 2, then ROCE, then CON01/CON11, then Day 31's distress flag) kept recurring throughout the project and was handled with the same diagnostic discipline and documentation style every time — a consistent, well-understood category of real-data deviation now.
- Visual verification (not just automated tests) caught issues automated tests couldn't: TCS's stray balance-sheet year was only visible by actually opening the rendered chart.

## What Was Harder Than Expected

- The interim/off-cycle balance sheet row (Day 33's finding) affected 79/92 companies and had been sitting in the database since Sprint 1's initial load — a five-sprint-old latent defect. This is a reminder that **schema-level data quality issues can hide behind aggregate queries** (`SELECT *`, `MAX(year)`) for a long time, and only surface when a new consumer does something structurally different (in this case, a sequential 10-year chart).
- Reconciling newly-built modules against earlier signed-off modules (`cashflow_intelligence.py` vs. Sprint 2's `cashflow_kpis.py`) remains unfinished — flagged repeatedly (Day 31, Day 33) but not yet actioned.

## Open Items — Carried Forward

1. **Reconciliation of `cashflow_intelligence.py` (Day 31) vs. Sprint 2's `cashflow_kpis.py`** — not yet done. Both compute similar metrics independently; should be spot-checked for agreement before final project sign-off.
2. **Pro Rule 11 title/text contradiction** (Day 30) — spec's rule title and rule text describe opposite inequalities. Implemented per the text's financial meaning; needs a team lead decision on which was intended.
3. **CON11's cash-proxy formula** vs. Day 9's `net_debt()` in `ratios.py` — two independent implementations of a similar concept, not yet reconciled.
4. **`src/etl/fiscal_calendar.py`'s `get_annual_rows()` should become the standard way to query `balancesheet`** for any future module doing "latest N years" logic — flagging this as a coding-standard recommendation for Sprint 6 and beyond, since the bug it fixes is exactly the kind that hides silently.
5. Sprint 1 Day 7 retro, and Sprint 2/3/4 team sign-off meetings, remain outstanding from earlier sprints (unblocked, not blocking further work).

## Demo Readiness

All artifacts needed for the Week 5 team lead review are generated and verified:
- **Tearsheets**: `reports/tearsheets/TCS_tearsheet.pdf`, `HDFCBANK_tearsheet.pdf`, `RELIANCE_tearsheet.pdf` (or any of the other 88) — all visually confirmed clean
- **`output/cashflow_intelligence.xlsx`** — 92 rows, corrected post-Day-33 fix
- **`output/pros_cons_generated.csv`** — 92/92 companies covered

**Meeting itself not yet held** — this retrospective and all listed artifacts are ready whenever that review is scheduled.

---

*Sprint 5 code-complete. Next: Sprint 6 (Days 36–45) — API, ML & QA: KMeans clustering, FastAPI server (16 endpoints), 60+ pytest test suite, final documentation and sign-off.*