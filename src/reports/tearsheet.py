"""
src/reports/tearsheet.py

Day 33 — Sprint 5, Module 8 (PDF Report Generator)
Two-page company tearsheet using ReportLab.

Page 1: navy header bar (company name + ticker), 6 KPI tiles (2 rows x 3),
         10yr Revenue/Net Profit bar chart, ROE/ROCE dual-axis line chart.
Page 2: Balance Sheet composition stacked bar, Cash Flow waterfall (latest
         year), Pros (green bullets), Cons (red bullets), Capital
         Allocation badge.

Charts are rendered via matplotlib to temporary PNGs, then embedded into
the ReportLab document as Image flowables — the standard pattern for
combining chart libraries with ReportLab's page layout engine.

WORDWRAP requirement: all text that could overflow (company names,
pros/cons bullets) uses ReportLab Paragraph flowables inside table cells,
which wrap automatically within their allotted column width. Raw strings
are never placed directly into a fixed-width Table cell.

Sanity-bound masking (Day 13/17/18 convention, ±500%) applied to ROE/ROCE
before display, so HAL/BEL/INDIGO/ICICIPRULI/HDFCLIFE-style balance-sheet
artifacts don't corrupt a tearsheet's KPI tiles or trend chart.

Test harness (Day 33): generates tearsheets for 5 companies spanning
different sectors (TCS/IT, HDFCBANK/Financials, RELIANCE/Energy,
SUNPHARMA/Healthcare, TATASTEEL/Materials) into reports/tearsheets_test/
and reports success/failure, file size, and which charts were skipped
per company — so overflow/layout issues are caught before Day 34's
92-company batch run.

Day 33 fix: all three chart functions that call ax.set_xticklabels() now
call ax.set_xticks() with explicit numeric positions FIRST. Plotting
directly against a list of year-label strings (the original approach)
triggered "UserWarning: set_ticklabels() should only be used with a
fixed number of ticks" — matplotlib was implicitly treating the strings
as categorical tick positions, which works today but risks silent
tick/label misalignment if any chart's axis ever rescales (e.g. a company
with an unusual year-range shape). Fixed by plotting against explicit
integer x-positions (range(len(years))) and only using the year strings
as tick labels, in all three affected chart functions.
"""

import csv
import logging
import sqlite3
import tempfile
from pathlib import Path
from typing import Optional

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    Image,
    PageBreak,
)
from src.etl.fiscal_calendar import get_annual_rows

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "data" / "nifty100.db"
OUTPUT_DIR = PROJECT_ROOT / "output"
PROS_CONS_CSV = OUTPUT_DIR / "pros_cons_generated.csv"
CAPITAL_ALLOC_CSV = OUTPUT_DIR / "capital_allocation.csv"
TEARSHEETS_DIR = PROJECT_ROOT / "reports" / "tearsheets"
TEST_DIR = PROJECT_ROOT / "reports" / "tearsheets_test"

NAVY = colors.HexColor("#1F4E78")
GREEN = colors.HexColor("#2E7D32")
RED = colors.HexColor("#C62828")

SANITY_BOUND_PCT = 500.0

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

PAGE_W, PAGE_H = A4
MARGIN = 2 * cm
USABLE_WIDTH = PAGE_W - 2 * MARGIN


def get_connection() -> sqlite3.Connection:
    """Get connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def is_implausible_pct(value: Optional[float]) -> bool:
    """Is implausible pct."""
    return value is not None and abs(value) > SANITY_BOUND_PCT


# --------------------------------------------------------------------------
# Data gathering
# --------------------------------------------------------------------------


def get_company_data(conn: sqlite3.Connection, company_id: str) -> dict:
    """Get company data."""
    company = conn.execute(
        "SELECT * FROM companies WHERE id = ?", (company_id,)
    ).fetchone()
    if company is None:
        raise ValueError(f"{company_id} not found in companies table")

    sector_row = conn.execute(
        "SELECT broad_sector FROM sectors WHERE company_id = ?", (company_id,)
    ).fetchone()

    fr_rows = [
        dict(r)
        for r in conn.execute(
            "SELECT * FROM financial_ratios WHERE company_id = ? ORDER BY year ASC",
            (company_id,),
        )
    ]
    pl_rows = [
        dict(r)
        for r in conn.execute(
            "SELECT * FROM profitandloss WHERE company_id = ? ORDER BY year ASC",
            (company_id,),
        )
    ]
    # Day 33 fix: filter out off-cycle interim rows (e.g. 2024-09) so the
    # 10yr BS composition chart shows a real annual sequence, not a mix
    # of annual + half-year snapshots.
    bs_rows_desc = get_annual_rows(conn, company_id, "balancesheet", "*")
    bs_rows = [dict(r) for r in reversed(bs_rows_desc)]  # back to ascending order
    cf_rows = [
        dict(r)
        for r in conn.execute(
            "SELECT * FROM cashflow WHERE company_id = ? ORDER BY year ASC",
            (company_id,),
        )
    ]

    return {
        "company_id": company_id,
        "company_name": company["company_name"],
        "sector": sector_row["broad_sector"] if sector_row else "Unknown",
        "fr": fr_rows,
        "pl": pl_rows,
        "bs": bs_rows,
        "cf": cf_rows,
    }


def load_pros_cons(company_id: str) -> tuple[list[str], list[str]]:
    """Load pros cons."""
    if not PROS_CONS_CSV.exists():
        return [], []
    pros, cons = [], []
    with open(PROS_CONS_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["company_id"] != company_id:
                continue
            if row["type"] == "pro":
                pros.append(row["text"])
            else:
                cons.append(row["text"])
    return pros, cons


def load_capital_allocation_label(company_id: str) -> Optional[str]:
    """Load capital allocation label."""
    if not CAPITAL_ALLOC_CSV.exists():
        return None
    latest_year, latest_label = None, None
    with open(CAPITAL_ALLOC_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["company_id"] != company_id:
                continue
            if latest_year is None or row["year"] > latest_year:
                latest_year, latest_label = row["year"], row["pattern_label"]
    return latest_label


# --------------------------------------------------------------------------
# KPI tiles
# --------------------------------------------------------------------------


def get_kpi_tiles(data: dict) -> list[tuple[str, str]]:
    """Returns 6 (label, formatted_value) pairs from the latest fr row.
    Sanity-bound masking applied to ROE/ROCE per Day 13/17/18 convention."""
    if not data["fr"]:
        return [("No data", "—")] * 6

    latest = data["fr"][-1]

    def fmt_pct(val, mask=False):
        """Fmt pct."""
        if val is None or (mask and is_implausible_pct(val)):
            return "N/A"
        return f"{val:.1f}%"

    def fmt_ratio(val):
        """Fmt ratio."""
        return "N/A" if val is None else f"{val:.2f}x"

    def fmt_cr(val):
        """Fmt cr."""
        return "N/A" if val is None else f"Rs {val:,.0f} Cr"

    return [
        ("ROE", fmt_pct(latest.get("return_on_equity_pct"), mask=True)),
        ("ROCE", fmt_pct(latest.get("return_on_capital_employed_pct"), mask=True)),
        ("D/E", fmt_ratio(latest.get("debt_to_equity"))),
        ("OPM", fmt_pct(latest.get("operating_profit_margin_pct"))),
        ("Revenue CAGR 5yr", fmt_pct(latest.get("revenue_cagr_5yr"))),
        ("Free Cash Flow", fmt_cr(latest.get("free_cash_flow_cr"))),
    ]


# --------------------------------------------------------------------------
# Charts (matplotlib -> PNG -> ReportLab Image)
# --------------------------------------------------------------------------


def chart_revenue_np(data: dict, tmp_dir: Path) -> Optional[Path]:
    """Chart revenue np."""
    rows = data["pl"][-10:]
    rows = [
        r
        for r in rows
        if r.get("sales") is not None and r.get("net_profit") is not None
    ]
    if len(rows) < 2:
        return None

    years = [r["year"] for r in rows]
    sales = [r["sales"] for r in rows]
    profit = [r["net_profit"] for r in rows]

    fig, ax = plt.subplots(figsize=(5.2, 2.6), dpi=150)
    x = list(range(len(years)))
    width = 0.38
    ax.bar([i - width / 2 for i in x], sales, width, label="Revenue", color="#1F4E78")
    ax.bar(
        [i + width / 2 for i in x], profit, width, label="Net Profit", color="#4CAF50"
    )
    ax.set_xticks(x)
    ax.set_xticklabels(years, rotation=45, ha="right", fontsize=6)
    ax.set_ylabel("Rs Cr", fontsize=7)
    ax.set_title("Revenue & Net Profit (10yr)", fontsize=8)
    ax.legend(fontsize=6)
    ax.tick_params(axis="y", labelsize=6)
    fig.tight_layout()

    path = tmp_dir / f"{data['company_id']}_rev_np.png"
    fig.savefig(path)
    plt.close(fig)
    return path


def chart_roe_roce(data: dict, tmp_dir: Path) -> Optional[Path]:
    """Chart roe roce."""
    rows = data["fr"][-10:]
    rows = [
        r
        for r in rows
        if r.get("return_on_equity_pct") is not None
        and not is_implausible_pct(r.get("return_on_equity_pct"))
        and r.get("return_on_capital_employed_pct") is not None
        and not is_implausible_pct(r.get("return_on_capital_employed_pct"))
    ]
    if len(rows) < 2:
        return None

    years = [r["year"] for r in rows]
    roe = [r["return_on_equity_pct"] for r in rows]
    roce = [r["return_on_capital_employed_pct"] for r in rows]

    fig, ax = plt.subplots(figsize=(5.2, 2.6), dpi=150)
    x = list(range(len(years)))
    ax.plot(
        x, roe, marker="o", label="ROE %", color="#1F4E78", linewidth=1.5, markersize=3
    )
    ax.plot(
        x,
        roce,
        marker="s",
        label="ROCE %",
        color="#C62828",
        linewidth=1.5,
        markersize=3,
    )
    ax.set_xticks(x)
    ax.set_xticklabels(years, rotation=45, ha="right", fontsize=6)
    ax.set_ylabel("%", fontsize=7)
    ax.set_title("ROE vs ROCE (10yr)", fontsize=8)
    ax.legend(fontsize=6)
    ax.tick_params(axis="y", labelsize=6)
    fig.tight_layout()

    path = tmp_dir / f"{data['company_id']}_roe_roce.png"
    fig.savefig(path)
    plt.close(fig)
    return path


def chart_bs_composition(data: dict, tmp_dir: Path) -> Optional[Path]:
    """Chart bs composition."""
    rows = data["bs"][-10:]
    rows = [
        r
        for r in rows
        if r.get("equity_capital") is not None and r.get("reserves") is not None
    ]
    if len(rows) < 2:
        return None

    years = [r["year"] for r in rows]
    equity = [(r["equity_capital"] or 0) + (r["reserves"] or 0) for r in rows]
    borrowings = [r.get("borrowings") or 0 for r in rows]
    other_liab = [r.get("other_liabilities") or 0 for r in rows]

    fig, ax = plt.subplots(figsize=(5.2, 2.6), dpi=150)
    x = list(range(len(years)))
    ax.bar(x, equity, label="Equity+Reserves", color="#1F4E78")
    ax.bar(x, borrowings, bottom=equity, label="Borrowings", color="#C62828")
    bottom2 = [e + b for e, b in zip(equity, borrowings)]
    ax.bar(x, other_liab, bottom=bottom2, label="Other Liabilities", color="#9E9E9E")
    ax.set_xticks(x)
    ax.set_xticklabels(years, rotation=45, ha="right", fontsize=6)
    ax.set_ylabel("Rs Cr", fontsize=7)
    ax.set_title("Balance Sheet Composition (10yr)", fontsize=8)
    ax.legend(fontsize=6)
    ax.tick_params(axis="y", labelsize=6)
    fig.tight_layout()

    path = tmp_dir / f"{data['company_id']}_bs.png"
    fig.savefig(path)
    plt.close(fig)
    return path


def chart_cf_waterfall(data: dict, tmp_dir: Path) -> Optional[Path]:
    """Chart cf waterfall."""
    if not data["cf"]:
        return None
    latest = data["cf"][-1]
    cfo = latest.get("operating_activity")
    cfi = latest.get("investing_activity")
    cff = latest.get("financing_activity")
    net = latest.get("net_cash_flow")
    if None in (cfo, cfi, cff):
        return None
    if net is None:
        net = cfo + cfi + cff

    labels = ["CFO", "CFI", "CFF", "Net Cash Flow"]
    values = [cfo, cfi, cff, net]
    colors_list = ["#4CAF50" if v >= 0 else "#C62828" for v in values[:3]] + ["#1F4E78"]

    fig, ax = plt.subplots(figsize=(5.2, 2.6), dpi=150)
    ax.bar(labels, values, color=colors_list)
    ax.axhline(0, color="black", linewidth=0.5)
    ax.set_ylabel("Rs Cr", fontsize=7)
    ax.set_title(f"Cash Flow Waterfall ({latest['year']})", fontsize=8)
    ax.tick_params(axis="both", labelsize=6)
    fig.tight_layout()

    path = tmp_dir / f"{data['company_id']}_cf.png"
    fig.savefig(path)
    plt.close(fig)
    return path


# --------------------------------------------------------------------------
# PDF building
# --------------------------------------------------------------------------


def build_kpi_tile_table(tiles: list[tuple[str, str]]) -> Table:
    """Build kpi tile table."""
    styles = getSampleStyleSheet()
    tile_label_style = ParagraphStyle(
        "tile_label",
        parent=styles["Normal"],
        fontSize=7,
        textColor=colors.white,
        alignment=1,
    )
    tile_value_style = ParagraphStyle(
        "tile_value",
        parent=styles["Normal"],
        fontSize=12,
        textColor=colors.white,
        alignment=1,
        fontName="Helvetica-Bold",
    )

    tile_flowables = []
    for label, value in tiles:
        inner = Table(
            [
                [Paragraph(label, tile_label_style)],
                [Paragraph(value, tile_value_style)],
            ],
            colWidths=[USABLE_WIDTH / 3 - 6],
        )
        inner.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.white),
                ]
            )
        )
        tile_flowables.append(inner)

    row1, row2 = tile_flowables[:3], tile_flowables[3:]
    grid = Table([row1, row2], colWidths=[USABLE_WIDTH / 3] * 3)
    grid.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return grid


def build_header(company_name: str, ticker: str, sector: str) -> Table:
    """Build header."""
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "header_title",
        parent=styles["Normal"],
        fontSize=16,
        textColor=colors.white,
        fontName="Helvetica-Bold",
    )
    sub_style = ParagraphStyle(
        "header_sub", parent=styles["Normal"], fontSize=10, textColor=colors.white
    )

    # Paragraph wraps automatically -> no overflow even for long legal names
    content = [
        [Paragraph(f"{company_name} ({ticker})", title_style)],
        [Paragraph(f"Sector: {sector}", sub_style)],
    ]
    header = Table(content, colWidths=[USABLE_WIDTH])
    header.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return header


def build_pros_cons_section(pros: list[str], cons: list[str]) -> list:
    """Build pros cons section."""
    styles = getSampleStyleSheet()
    pro_style = ParagraphStyle(
        "pro",
        parent=styles["Normal"],
        fontSize=8,
        textColor=GREEN,
        leftIndent=10,
        spaceAfter=3,
    )
    con_style = ParagraphStyle(
        "con",
        parent=styles["Normal"],
        fontSize=8,
        textColor=RED,
        leftIndent=10,
        spaceAfter=3,
    )
    heading_style = ParagraphStyle(
        "section_heading",
        parent=styles["Heading3"],
        fontSize=10,
        spaceBefore=6,
        spaceAfter=4,
    )

    elements = [Paragraph("Pros", heading_style)]
    if pros:
        for p in pros:
            # Paragraph wraps long text within its column width automatically
            # — this is how the spec's WORDWRAP requirement is satisfied.
            elements.append(Paragraph(f"&#8226; {p}", pro_style))
    else:
        elements.append(Paragraph("No pros identified.", pro_style))

    elements.append(Paragraph("Cons", heading_style))
    if cons:
        for c in cons:
            elements.append(Paragraph(f"&#8226; {c}", con_style))
    else:
        elements.append(Paragraph("No cons identified.", con_style))

    return elements


def build_capital_allocation_badge(label: Optional[str]) -> Table:
    """Build capital allocation badge."""
    styles = getSampleStyleSheet()
    badge_style = ParagraphStyle(
        "badge",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.white,
        alignment=1,
        fontName="Helvetica-Bold",
    )
    text = label if label else "Not Available"
    badge = Table(
        [[Paragraph(f"Capital Allocation: {text}", badge_style)]],
        colWidths=[USABLE_WIDTH],
    )
    badge.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return badge


def build_tearsheet(
    conn: sqlite3.Connection, company_id: str, output_path: Path, tmp_dir: Path
) -> dict:
    """Builds one 2-page tearsheet. Returns a diagnostic dict (not just a
    pass/fail bool) so the test harness can report exactly which charts
    were skipped for which company."""
    data = get_company_data(conn, company_id)
    pros, cons = load_pros_cons(company_id)
    alloc_label = load_capital_allocation_label(company_id)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
    )

    styles = getSampleStyleSheet()
    story = []
    diag = {"company_id": company_id, "charts_rendered": [], "charts_skipped": []}

    # --- Page 1 ---
    story.append(build_header(data["company_name"], company_id, data["sector"]))
    story.append(Spacer(1, 10))
    story.append(build_kpi_tile_table(get_kpi_tiles(data)))
    story.append(Spacer(1, 10))

    rev_np_path = chart_revenue_np(data, tmp_dir)
    if rev_np_path:
        story.append(
            Image(str(rev_np_path), width=USABLE_WIDTH, height=USABLE_WIDTH * 0.38)
        )
        diag["charts_rendered"].append("revenue_np")
    else:
        story.append(
            Paragraph(
                "Revenue/Net Profit chart unavailable — insufficient P&L history.",
                styles["Normal"],
            )
        )
        diag["charts_skipped"].append("revenue_np")

    story.append(Spacer(1, 6))

    roe_roce_path = chart_roe_roce(data, tmp_dir)
    if roe_roce_path:
        story.append(
            Image(str(roe_roce_path), width=USABLE_WIDTH, height=USABLE_WIDTH * 0.38)
        )
        diag["charts_rendered"].append("roe_roce")
    else:
        story.append(
            Paragraph(
                "ROE/ROCE chart unavailable — insufficient or sanity-masked history.",
                styles["Normal"],
            )
        )
        diag["charts_skipped"].append("roe_roce")

    story.append(PageBreak())

    # --- Page 2 ---
    bs_path = chart_bs_composition(data, tmp_dir)
    if bs_path:
        story.append(
            Image(str(bs_path), width=USABLE_WIDTH, height=USABLE_WIDTH * 0.38)
        )
        diag["charts_rendered"].append("bs_composition")
    else:
        story.append(
            Paragraph(
                "Balance Sheet composition chart unavailable — insufficient BS history (e.g. SBIN-style gap).",
                styles["Normal"],
            )
        )
        diag["charts_skipped"].append("bs_composition")

    story.append(Spacer(1, 6))

    cf_path = chart_cf_waterfall(data, tmp_dir)
    if cf_path:
        story.append(
            Image(str(cf_path), width=USABLE_WIDTH, height=USABLE_WIDTH * 0.38)
        )
        diag["charts_rendered"].append("cf_waterfall")
    else:
        story.append(
            Paragraph(
                "Cash Flow waterfall unavailable — no cash flow data for latest year.",
                styles["Normal"],
            )
        )
        diag["charts_skipped"].append("cf_waterfall")

    story.append(Spacer(1, 8))
    story.extend(build_pros_cons_section(pros, cons))
    story.append(Spacer(1, 8))
    story.append(build_capital_allocation_badge(alloc_label))

    doc.build(story)

    diag["file_size_kb"] = round(output_path.stat().st_size / 1024, 1)
    diag["pros_count"] = len(pros)
    diag["cons_count"] = len(cons)
    return diag


# --------------------------------------------------------------------------
# Test harness — Day 33: 5 companies from different sectors
# --------------------------------------------------------------------------

TEST_COMPANIES = ["TCS", "HDFCBANK", "RELIANCE", "SUNPHARMA", "TATASTEEL"]


def main() -> None:
    """Main."""
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found at {DB_PATH}")

    TEST_DIR.mkdir(parents=True, exist_ok=True)
    conn = get_connection()

    results = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        for company_id in TEST_COMPANIES:
            output_path = TEST_DIR / f"{company_id}_tearsheet.pdf"
            try:
                diag = build_tearsheet(conn, company_id, output_path, tmp_dir)
                diag["status"] = "OK"
            except Exception as e:
                diag = {"company_id": company_id, "status": f"FAILED: {e}"}
            results.append(diag)

    conn.close()

    print("\n=== Day 33 Test Summary (5 companies) ===")
    for r in results:
        print(f"\n{r['company_id']}: {r.get('status')}")
        if r.get("status") == "OK":
            print(f"  File size: {r['file_size_kb']} KB")
            print(f"  Charts rendered: {r['charts_rendered']}")
            print(f"  Charts skipped:  {r['charts_skipped']}")
            print(f"  Pros: {r['pros_count']}, Cons: {r['cons_count']}")


if __name__ == "__main__":
    main()
