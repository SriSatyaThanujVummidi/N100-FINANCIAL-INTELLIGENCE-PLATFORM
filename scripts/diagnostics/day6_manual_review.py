"""Day 6 — Manual Data Quality Review.

1. Picks 5 random companies (fixed seed -> reproducible) and dumps their
   full profile across all 12 tables for manual cross-check against the
   source Excel files.
2. Checks year coverage for ALL 92 companies in P&L/BS/CF, flags any with
   < 5 years combined history (DQ-16).
3. Re-verifies the 3 known edge-case companies (TVSMOTOR, PNB, ADANIENSOL)
   to confirm Day 5's fixes are reflected correctly in the loaded DB.

Writes output/day6_dq_review.md as the reviewable artifact.
"""
import random
import sqlite3
from pathlib import Path

DB_PATH = Path("data/nifty100.db")
SEED = 42  # fixed seed -> reproducible "random" sample, documented in output


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def fetch_all(conn, query, params=()):
    return [dict(r) for r in conn.execute(query, params).fetchall()]


def company_profile(conn, cid):
    lines = [f"## {cid}"]
    company = fetch_all(conn, "SELECT * FROM companies WHERE id=?", (cid,))
    if not company:
        lines.append("- NOT FOUND in companies table.")
        return "\n".join(lines)

    c = company[0]
    lines.append(f"- Name: {c['company_name']}")
    lines.append(f"- face_value={c['face_value']}, book_value={c['book_value']}, "
                  f"roce%={c['roce_percentage']}, roe%={c['roe_percentage']}")

    sector = fetch_all(conn, "SELECT * FROM sectors WHERE company_id=?", (cid,))
    if sector:
        s = sector[0]
        lines.append(f"- Sector: {s['broad_sector']} / {s['sub_sector']} (weight {s['index_weight_pct']}%)")

    for table in ["profitandloss", "balancesheet", "cashflow", "financial_ratios"]:
        rows = fetch_all(conn, f"SELECT year FROM {table} WHERE company_id=? ORDER BY year", (cid,))
        years = [r["year"] for r in rows]
        flag = "  <-- DQ-16: fewer than 5 years!" if len(years) < 5 else ""
        lines.append(f"- {table}: {len(years)} years -> {years}{flag}")

    latest_pl = fetch_all(conn, "SELECT * FROM profitandloss WHERE company_id=? ORDER BY year DESC LIMIT 1", (cid,))
    if latest_pl:
        p = latest_pl[0]
        lines.append(f"- Latest P&L ({p['year']}): sales={p['sales']}, expenses={p['expenses']}, "
                      f"operating_profit={p['operating_profit']}, opm%={p['opm_percentage']}, net_profit={p['net_profit']}")

    latest_bs = fetch_all(conn, "SELECT * FROM balancesheet WHERE company_id=? ORDER BY year DESC LIMIT 1", (cid,))
    if latest_bs:
        b = latest_bs[0]
        diff = None
        if b["total_assets"] not in (None, 0):
            diff = round(abs(b["total_assets"] - b["total_liabilities"]) / abs(b["total_assets"]) * 100, 2)
        lines.append(f"- Latest BS ({b['year']}): total_assets={b['total_assets']}, "
                      f"total_liabilities={b['total_liabilities']}" + (f" (diff={diff}%)" if diff is not None else ""))

    latest_cf = fetch_all(conn, "SELECT * FROM cashflow WHERE company_id=? ORDER BY year DESC LIMIT 1", (cid,))
    if latest_cf:
        cf = latest_cf[0]
        lines.append(f"- Latest CF ({cf['year']}): CFO={cf['operating_activity']}, CFI={cf['investing_activity']}, "
                      f"CFF={cf['financing_activity']}, net_cash_flow={cf['net_cash_flow']}")

    doc_count = fetch_all(conn, "SELECT COUNT(*) as n FROM documents WHERE company_id=?", (cid,))[0]["n"]
    pros_count = fetch_all(conn, "SELECT COUNT(*) as n FROM prosandcons WHERE company_id=?", (cid,))[0]["n"]
    peer_count = fetch_all(conn, "SELECT COUNT(*) as n FROM peer_groups WHERE company_id=?", (cid,))[0]["n"]
    lines.append(f"- documents={doc_count}, prosandcons={pros_count}, peer_groups membership={peer_count}")

    return "\n".join(lines)


def main():
    conn = get_conn()
    all_ids = [r["id"] for r in fetch_all(conn, "SELECT id FROM companies ORDER BY id")]
    print(f"Companies in DB: {len(all_ids)}")

    random.seed(SEED)
    sample_size = min(5, len(all_ids))
    sample = random.sample(all_ids, sample_size)

    report = ["# Day 6 — Manual Data Quality Review\n", f"Random sample (seed={SEED}): {sample}\n"]

    report.append("## Part 1 — Full profile dump for manual cross-check against source Excel\n")
    for cid in sample:
        report.append(company_profile(conn, cid))
        report.append("")

    report.append("## Part 2 — Year coverage check, all companies (DQ-16: flag < 5 years)\n")
    low_coverage = []
    for cid in all_ids:
        pl_years = len(fetch_all(conn, "SELECT DISTINCT year FROM profitandloss WHERE company_id=?", (cid,)))
        bs_years = len(fetch_all(conn, "SELECT DISTINCT year FROM balancesheet WHERE company_id=?", (cid,)))
        cf_years = len(fetch_all(conn, "SELECT DISTINCT year FROM cashflow WHERE company_id=?", (cid,)))
        min_years = min(pl_years, bs_years, cf_years)
        if min_years < 5:
            low_coverage.append((cid, pl_years, bs_years, cf_years, min_years))

    if low_coverage:
        report.append(f"**{len(low_coverage)} companies below 5-year combined coverage:**\n")
        report.append("| company_id | P&L yrs | BS yrs | CF yrs | min |")
        report.append("|---|---|---|---|---|")
        for cid, p, b, c, m in low_coverage:
            report.append(f"| {cid} | {p} | {b} | {c} | {m} |")
    else:
        report.append("No companies below 5-year combined coverage.")
    report.append("")

    report.append("## Part 3 — Re-verify the 3 known Day-5 edge-case companies\n")
    for cid in ["TVSMOTOR", "PNB", "ADANIENSOL"]:
        report.append(company_profile(conn, cid))
        report.append("")

    out_path = Path("output/day6_dq_review.md")
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text("\n".join(report), encoding="utf-8")
    print(f"Wrote {out_path}")
    print(f"Random sample selected: {sample}")
    print(f"Low-coverage companies (<5yr): {len(low_coverage)}")
    conn.close()


if __name__ == "__main__":
    main()