"""
src/nlp/day30_diagnose_nodata.py
"""

import csv
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = PROJECT_ROOT / "output" / "pros_cons_generated.csv"

KNOWN_THIN_DATA = {
    "SBIN",
    "JIOFIN",
    "HAL",
    "BEL",
    "INDIGO",
    "ICICIPRULI",
    "HDFCLIFE",
    "LICI",
    "ATGL",
}


def main() -> None:
    """Main."""
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    nodata_rows = [r for r in rows if r["rule_id"] == "NODATA_FALLBACK"]
    by_type = Counter(r["type"] for r in nodata_rows)
    print(f"Total NODATA_FALLBACK rows: {len(nodata_rows)}")
    print(f"  pro-side: {by_type['pro']}")
    print(f"  con-side: {by_type['con']}")

    print("\nCompanies with NODATA_FALLBACK, by side:")
    for r in nodata_rows:
        flag = (
            " <- KNOWN THIN-DATA COMPANY" if r["company_id"] in KNOWN_THIN_DATA else ""
        )
        print(f"  {r['company_id']:15s} {r['type']:4s}{flag}")

    nodata_companies = {r["company_id"] for r in nodata_rows}
    unexplained = nodata_companies - KNOWN_THIN_DATA
    print(f"\nNODATA companies NOT in the known thin-data list: {len(unexplained)}")
    print(f"  {sorted(unexplained)}")

    import sqlite3

    conn = sqlite3.connect(PROJECT_ROOT / "data" / "nifty100.db")
    conn.row_factory = sqlite3.Row
    company_ids = sorted(r["id"] for r in conn.execute("SELECT id FROM companies"))

    print("\n--- CON11 (Net Debt / EBITDA) sanity check ---")
    ratios = []
    for cid in company_ids:
        bs = conn.execute(
            "SELECT borrowings, investments, other_asset FROM balancesheet "
            "WHERE company_id = ? ORDER BY year DESC LIMIT 1",
            (cid,),
        ).fetchone()
        pl = conn.execute(
            "SELECT operating_profit FROM profitandloss "
            "WHERE company_id = ? ORDER BY year DESC LIMIT 1",
            (cid,),
        ).fetchone()
        if bs is None or pl is None:
            continue
        borrowings, investments, other_asset = (
            bs["borrowings"],
            bs["investments"],
            bs["other_asset"],
        )
        ebitda = pl["operating_profit"]
        if None in (borrowings, investments, other_asset, ebitda) or ebitda <= 0:
            continue
        net_debt = borrowings - investments - other_asset
        ratio = net_debt / ebitda
        ratios.append((cid, net_debt, ebitda, ratio))

    ratios.sort(key=lambda x: x[3], reverse=True)
    print(f"Companies with a computable ratio: {len(ratios)} / {len(company_ids)}")
    print("Top 10 by ratio:")
    for cid, nd, ebitda, ratio in ratios[:10]:
        print(
            f"  {cid:15s} net_debt={nd:>12,.0f}  ebitda={ebitda:>10,.0f}  ratio={ratio:>8.2f}"
        )
    print("Bottom 5 by ratio (most negative net debt / net cash):")
    for cid, nd, ebitda, ratio in ratios[-5:]:
        print(
            f"  {cid:15s} net_debt={nd:>12,.0f}  ebitda={ebitda:>10,.0f}  ratio={ratio:>8.2f}"
        )

    print("\n--- Investigating pro-side NODATA companies ---")
    from src.nlp.pros_cons_generator import build_company_context, PRO_RULES

    for cid in ["BHEL", "GODREJCP", "JINDALSTEL"]:
        ctx = build_company_context(conn, cid)
        print(f"\n{cid}:")
        print(
            f"  fr rows: {len(ctx['fr'])}, pl rows: {len(ctx['pl'])}, bs rows: {len(ctx['bs'])}, mkt: {'yes' if ctx['mkt'] else 'no'}"
        )
        if ctx["fr"]:
            latest = ctx["fr"][-1]
            print(
                f"  latest year: roe={latest['return_on_equity_pct']}, roce={latest['return_on_capital_employed_pct']}, "
                f"de={latest['debt_to_equity']}, opm={latest['operating_profit_margin_pct']}, "
                f"rev_cagr5={latest['revenue_cagr_5yr']}, pat_cagr5={latest['pat_cagr_5yr']}, "
                f"eps_cagr5={latest['eps_cagr_5yr']}, icr={latest['interest_coverage']}, fcf={latest['free_cash_flow_cr']}"
            )
        for rule_id, fn in PRO_RULES:
            result = fn(ctx)
            print(f"    {rule_id}: {result}")

    conn.close()


if __name__ == "__main__":
    main()
