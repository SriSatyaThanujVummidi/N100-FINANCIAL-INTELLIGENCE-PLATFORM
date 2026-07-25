"""Day 27 — Backend smoke test.

Exercises every db.py function against 10 deliberately chosen tickers
(5 normal across different sectors + 5 documented edge cases) to catch
crashes fast, before manual browser testing. This does NOT test Streamlit
rendering — only that the data layer doesn't throw for any of these
tickers. Run with: py -m src.dashboard.day27_qa_smoke_test
"""

import sys
import time
import traceback
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.dashboard.utils.db import (
    get_bs,
    get_cf,
    get_companies,
    get_documents,
    get_pl,
    get_prosandcons,
    get_ratios,
    get_valuation,
)

# 5 "normal" tickers across different sectors (spec Day 27's requirement:
# "IT, Financials, FMCG, Energy, Healthcare") + 5 documented edge cases.
TEST_TICKERS = {
    "TCS": "IT — normal case",
    "HDFCBANK": "Financials — normal case",
    "HINDUNILVR": "FMCG — normal case",
    "RELIANCE": "Energy — normal case",
    "SUNPHARMA": "Healthcare — normal case",
    "SBIN": "EDGE CASE — zero balance sheet rows (Day 6)",
    "HAL": "EDGE CASE — sanity-bound flagged ROE/ROCE (Day 13)",
    "JIOFIN": "EDGE CASE — 2-3yr history only (Day 6)",
    "SIEMENS": "EDGE CASE — Sep fiscal year-end (Day 15)",
    "PNB": "EDGE CASE — null operating_profit some years (Day 5)",
}

FUNCTIONS_TO_TEST = [
    ("get_ratios", lambda t: get_ratios(ticker=t)),
    ("get_pl", get_pl),
    ("get_bs", get_bs),
    ("get_cf", get_cf),
    ("get_documents", get_documents),
    ("get_prosandcons", get_prosandcons),
    ("get_valuation", lambda t: get_valuation(ticker=t)),
]


def main() -> None:
    """Main."""
    print("=" * 70)
    print("Day 27 QA — Backend Smoke Test")
    print("=" * 70)

    companies_df = get_companies()
    real_tickers = set(companies_df["id"].tolist())

    n_pass = 0
    n_fail = 0
    n_empty = 0

    for ticker, description in TEST_TICKERS.items():
        print(f"\n--- {ticker} ({description}) ---")

        if ticker not in real_tickers:
            print(f"  ⚠️  {ticker} not found in companies table — skipping")
            continue

        for func_name, func in FUNCTIONS_TO_TEST:
            try:
                start = time.time()
                result = func(ticker)
                elapsed = (time.time() - start) * 1000
                row_count = len(result)
                status = "empty" if row_count == 0 else f"{row_count} rows"
                print(f"  ✅ {func_name:20s} -> {status:12s} ({elapsed:.1f}ms)")
                if row_count == 0:
                    n_empty += 1
                n_pass += 1
            except Exception as exc:
                print(f"  ❌ {func_name:20s} -> CRASHED: {type(exc).__name__}: {exc}")
                traceback.print_exc()
                n_fail += 1

    print("\n" + "=" * 70)
    print(f"SUMMARY: {n_pass} calls passed, {n_fail} crashed, {n_empty} returned empty")
    print("=" * 70)

    if n_fail > 0:
        print(
            "\n⚠️  At least one function crashed — fix before manual browser testing."
        )
        sys.exit(1)
    else:
        print("\n✅ No backend crashes for any of the 10 test tickers.")


if __name__ == "__main__":
    main()
