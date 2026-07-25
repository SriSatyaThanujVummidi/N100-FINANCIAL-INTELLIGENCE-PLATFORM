# Day 43 — Performance & Integration Testing Notes

## 1. Concurrent Load Test — 10 simultaneous `/screener` calls

**Target:** all 10 complete within 10 seconds.

### First run (before fix)
- Total time: 2.245s (technically under 10s)
- **6 of 10 requests returned HTTP 500**, not 200
- This was NOT caught by only checking total duration — the original test only measured
  timing, not success/failure per request

### Root cause — real bug, found and fixed today

`sqlite3.ProgrammingError: SQLite objects created in a thread can only be used in that
same thread.`

FastAPI runs synchronous route handlers in a thread pool. Each request can be dispatched
to a different worker thread. `src/api/db.py`'s `get_connection()` created a SQLite
connection without `check_same_thread=False`, so whenever a connection was created on one
worker thread and closed (or used) on another — which happens routinely under concurrent
load with FastAPI's thread pool — SQLite raised a `ProgrammingError` and the request failed
with HTTP 500.

**This bug had been present in every API endpoint since Day 38** (`src/api/db.py`'s
`get_connection()` was written then and never changed since). It was never caught by any
single-request test across Days 38–42 because none of them exercised true concurrency —
it only surfaced once Day 43's load test ran 10 simultaneous requests.

**Fix:** one-line change in `src/api/db.py`:

```python
# Before:
conn = sqlite3.connect(DB_PATH)

# After:
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
```

Safe in this context because each request gets its own freshly-created connection object
(never shared or reused across concurrent requests) — `check_same_thread=False` just stops
SQLite from forbidding a single connection's creation and teardown from happening on
different threads, which is exactly what FastAPI's thread pool was doing to us.

### Second run (after fix)
- **10/10 requests returned 200**
- Total time: 2.114s
- Slowest individual call: 2.107s
- **PASS** — all requests succeeded, well within the 10s target

**Recommendation:** flag this fix for team lead review before Day 45 sign-off — this is
the kind of bug that would have failed silently in production the first time two users
hit the API at the same time (e.g. two browser tabs, or the dashboard plus an external
API consumer querying simultaneously).

---

## 2. Dashboard Performance — Company Profile screen, 5 tickers

**Target:** each ticker loads in under 3 seconds.

Simulated the query pattern `02_profile.py` runs (company + sector + full P&L/BS/CF
history + latest ratios), against the real database directly (not through the API, since
the dashboard reads SQLite directly).

| Ticker | Load time | Result |
|---|---|---|
| TCS | 1.3ms | PASS |
| RELIANCE | 0.6ms | PASS |
| SBIN | 0.4ms | PASS |
| HDFCBANK | 0.6ms | PASS |
| HAL | 0.5ms | PASS |

**Overall: PASS.** All 5 tickers load in under 1.5ms — roughly 2,000–7,000x faster than
the 3-second requirement. Consistent with Sprint 4 Day 27's already-documented backend
timing (6–16ms per ticker for a fuller smoke-test pass).

---

## 3. End-to-End Port Conflict Check

Streamlit (port 8501) and FastAPI/Uvicorn (port 8000) were run simultaneously in separate
terminals. Both confirmed reachable at the same time via direct HTTP checks:

- `GET http://localhost:8000/api/v1/health` → 200, full `db_row_counts` for all 12 tables
- `GET http://localhost:8501` → 200, Streamlit app HTML served correctly

**No port conflicts.** Both services run concurrently without interference.

---

## 4. SQLite Query Optimization

Added indexes on `company_id`/`year` for the five largest time-series tables
(`profitandloss`, `balancesheet`, `cashflow`, `financial_ratios`, `market_cap`) and
`company_id`-only indexes for four supporting tables (`stock_prices`, `documents`,
`prosandcons`, `sectors`).

**Note for team lead:** on inspection, a first set of indexes with different names
(`idx_pl_company`, `idx_bs_company`, `idx_cf_company`, etc.) already existed on the same
tables/columns, most likely created in Sprint 1's `schema.sql`. Today's indexes are
functionally redundant with those — not harmful, but duplicative. Recommend a follow-up
cleanup pass to drop one of the two overlapping sets rather than carrying both forward
into final delivery.

Given the dashboard and API were already performing at sub-millisecond to low-millisecond
speeds *before* this optimization pass (see sections 1–2), these indexes are a
defensive/best-practice addition rather than a fix for an observed bottleneck — no
performance problem was actually present in this dataset's scale (92 companies,
low-thousands of rows per table).

---

## Summary

| Item | Target | Result |
|---|---|---|
| 10 concurrent screener calls | <10s, all succeed | 2.114s, 10/10 succeeded (after fix) |
| Company Profile load, 5 tickers | <3s each | 0.4–1.3ms each |
| Dashboard + API simultaneous | No port conflicts | Confirmed, both reachable |
| SQLite indexes | Added on large tables | Done (duplicate set found, flagged for cleanup) |

**One real, previously-undetected bug found and fixed**: cross-thread SQLite connection
error under concurrent API load, present since Day 38, invisible to every prior
single-request test. Fixed via `check_same_thread=False` in `src/api/db.py`.