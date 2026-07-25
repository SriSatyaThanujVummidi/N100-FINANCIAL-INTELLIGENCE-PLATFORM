"""

Day 35 — Sprint 5, Module 8 (Portfolio Summary PDF)
One-page-per-company PDF, alphabetical by ticker. Each page: company
name, sector, top 6 KPIs, trend arrows (up/down/flat) vs prior year.

Trend arrow rule (spec): up if metric improved in latest year, down if
declined, flat (right arrow) if within 2% of prior year. "Improved"
depends on the metric's polarity — ROE/ROCE/OPM/Revenue CAGR/FCF are
higher-is-better; D/E is lower-is-better. Flat-band is evaluated on
relative % change for all metrics except D/E, which is compared on an
absolute-point basis (a "2% relative change" on a D/E of 0.05x is
sub-hundredth-of-a-point noise, not a meaningful trend).

Scope decision (documented, not silently applied): Day 34 excluded
JIOFIN from the tearsheet batch (needs 3+ yrs of P&L history for its
10-year charts). This module needs only a single YoY comparison, and
JIOFIN has exactly 2 reported years — enough for one comparison — so
JIOFIN IS included here. All 92 companies get a page. A company with
only 1 reported year (none currently, per Sprint 2 findings) would show
"N/A" trend arrows rather than being skipped entirely, since the KPI
values themselves are still valid to display even without a trend.

Sanity-bound masking (Day 13/17/18, ±500%) applied to ROE/ROCE before
display and before trend comparison, so a HAL/BEL/INDIGO/ICICIPRULI/
HDFCLIFE-style artifact can't produce a nonsensical trend arrow.
"""

import logging
import sqlite3
from pathlib import Path
from typing import Optional

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
    PageBreak,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "data" / "nifty100.db"
PORTFOLIO_DIR = PROJECT_ROOT / "reports" / "portfolio"
OUTPUT_PATH = PORTFOLIO_DIR / "portfolio_summary.pdf"

NAVY = colors.HexColor("#1F4E78")
LIGHT_GREY = colors.HexColor("#F2F2F2")
GREEN = colors.HexColor("#2E7D32")
RED = colors.HexColor("#C62828")
GREY = colors.HexColor("#757575")

SANITY_BOUND_PCT = 500.0
FLAT_BAND_PCT = 2.0

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

PAGE_W, PAGE_H = A4
MARGIN = 2 * cm
USABLE_WIDTH = PAGE_W - 2 * MARGIN

# metric_key -> (financial_ratios column, display label, polarity, unit)
# polarity: "higher" = higher is better, "lower" = lower is better
METRICS = [
    ("roe", "return_on_equity_pct", "ROE", "higher", "%"),
    ("roce", "return_on_capital_employed_pct", "ROCE", "higher", "%"),
    ("de", "debt_to_equity", "D/E", "lower", "x"),
    ("opm", "operating_profit_margin_pct", "OPM", "higher", "%"),
    ("revenue_cagr_5yr", "revenue_cagr_5yr", "Revenue CAGR 5yr", "higher", "%"),
    ("fcf", "free_cash_flow_cr", "Free Cash Flow", "higher", "Cr"),
]


def get_connection() -> sqlite3.Connection:
    """Get connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def is_implausible_pct(value: Optional[float]) -> bool:
    """Is implausible pct."""
    return value is not None and abs(value) > SANITY_BOUND_PCT


def get_last_two_years(
    conn: sqlite3.Connection, company_id: str
) -> tuple[Optional[dict], Optional[dict]]:
    """Returns (latest, prior) financial_ratios rows, or (latest, None)
    if only one year exists, or (None, None) if zero years exist."""
    rows = conn.execute(
        "SELECT * FROM financial_ratios WHERE company_id = ? ORDER BY year DESC LIMIT 2",
        (company_id,),
    ).fetchall()
    if len(rows) == 0:
        return None, None
    if len(rows) == 1:
        return dict(rows[0]), None
    return dict(rows[0]), dict(rows[1])


def trend_arrow(
    latest_val: Optional[float], prior_val: Optional[float], polarity: str
) -> str:
    """Returns 'up', 'down', 'flat', or 'na'."""
    if latest_val is None or prior_val is None:
        return "na"

    if prior_val == 0:
        # Can't compute relative change from a zero base; fall back to
        # absolute-direction only.
        if latest_val == 0:
            return "flat"
        direction = "up" if latest_val > 0 else "down"
    else:
        pct_change = (latest_val - prior_val) / abs(prior_val) * 100
        if abs(pct_change) <= FLAT_BAND_PCT:
            return "flat"
        direction = "up" if pct_change > 0 else "down"

    if polarity == "lower":
        # For lower-is-better metrics (D/E), an "up" value move is
        # actually a decline in quality, and vice versa.
        return (
            {"up": "down", "down": "up"}[direction]
            if direction in ("up", "down")
            else direction
        )
    return direction


def get_company_kpi_trends(conn: sqlite3.Connection, company_id: str) -> list[dict]:
    """Returns 6 dicts: {label, value_str, arrow}."""
    latest, prior = get_last_two_years(conn, company_id)

    results = []
    for key, column, label, polarity, unit in METRICS:
        latest_val = latest.get(column) if latest else None
        prior_val = prior.get(column) if prior else None

        # Sanity-bound masking for ROE/ROCE before display AND before
        # trend comparison (Day 13/17/18 convention).
        if key in ("roe", "roce"):
            if is_implausible_pct(latest_val):
                latest_val = None
            if is_implausible_pct(prior_val):
                prior_val = None

        if latest_val is None:
            value_str = "N/A"
        elif unit == "%":
            value_str = f"{latest_val:.1f}%"
        elif unit == "x":
            value_str = f"{latest_val:.2f}x"
        elif unit == "Cr":
            value_str = f"Rs {latest_val:,.0f} Cr"
        else:
            value_str = str(latest_val)

        arrow = trend_arrow(latest_val, prior_val, polarity)
        results.append({"label": label, "value_str": value_str, "arrow": arrow})

    return results


ARROW_SYMBOLS = {
    "up": ("\u2191", GREEN),
    "down": ("\u2193", RED),
    "flat": ("\u2192", GREY),
    "na": ("—", GREY),
}


def build_company_page(conn: sqlite3.Connection, company_id: str) -> list:
    """Returns the flowables for one company's page (does NOT include
    the trailing PageBreak — caller adds that between companies)."""
    company = conn.execute(
        "SELECT company_name FROM companies WHERE id = ?", (company_id,)
    ).fetchone()
    sector_row = conn.execute(
        "SELECT broad_sector FROM sectors WHERE company_id = ?", (company_id,)
    ).fetchone()
    company_name = company["company_name"] if company else company_id
    sector = sector_row["broad_sector"] if sector_row else "Unknown"

    kpis = get_company_kpi_trends(conn, company_id)

    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle(
        "title",
        parent=styles["Normal"],
        fontSize=16,
        textColor=colors.white,
        fontName="Helvetica-Bold",
    )
    sub_style = ParagraphStyle(
        "sub", parent=styles["Normal"], fontSize=10, textColor=colors.white
    )
    header = Table(
        [
            [Paragraph(f"{company_name} ({company_id})", title_style)],
            [Paragraph(f"Sector: {sector}", sub_style)],
        ],
        colWidths=[USABLE_WIDTH],
    )
    header.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(header)
    story.append(Spacer(1, 20))

    label_style = ParagraphStyle(
        "kpi_label", parent=styles["Normal"], fontSize=9, alignment=1
    )
    value_style = ParagraphStyle(
        "kpi_value",
        parent=styles["Normal"],
        fontSize=14,
        alignment=1,
        fontName="Helvetica-Bold",
    )
    arrow_style_template = ParagraphStyle(
        "kpi_arrow",
        parent=styles["Normal"],
        fontSize=14,
        alignment=1,
        fontName="Helvetica-Bold",
    )

    tile_flowables = []
    for kpi in kpis:
        symbol, color = ARROW_SYMBOLS[kpi["arrow"]]
        arrow_style = ParagraphStyle(
            "arrow_dynamic", parent=arrow_style_template, textColor=color
        )
        cell = Table(
            [
                [Paragraph(kpi["label"], label_style)],
                [Paragraph(kpi["value_str"], value_style)],
                [Paragraph(symbol, arrow_style)],
            ],
            colWidths=[USABLE_WIDTH / 3 - 6],
        )
        cell.setStyle(
            TableStyle(
                [
                    ("BOX", (0, 0), (-1, -1), 0.75, colors.grey),
                    ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GREY),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        tile_flowables.append(cell)

    row1, row2 = tile_flowables[:3], tile_flowables[3:]
    grid = Table([row1, row2], colWidths=[USABLE_WIDTH / 3] * 3)
    grid.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(grid)
    story.append(Spacer(1, 16))

    legend_style = ParagraphStyle(
        "legend", parent=styles["Normal"], fontSize=8, textColor=GREY
    )
    story.append(
        Paragraph(
            "&#8593; improved vs prior year &nbsp;&nbsp; &#8595; declined vs prior year &nbsp;&nbsp; "
            "&#8594; flat (within 2%) &nbsp;&nbsp; — not available",
            legend_style,
        )
    )

    return story


def main() -> None:
    """Main."""
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found at {DB_PATH}")

    PORTFOLIO_DIR.mkdir(parents=True, exist_ok=True)
    conn = get_connection()

    company_ids = sorted(r["id"] for r in conn.execute("SELECT id FROM companies"))
    logger.info("Building portfolio summary for %d companies", len(company_ids))

    doc = SimpleDocTemplate(
        str(OUTPUT_PATH),
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
    )

    full_story = []
    na_heavy_companies = []
    for i, company_id in enumerate(company_ids):
        page_story = build_company_page(conn, company_id)
        full_story.extend(page_story)
        if i < len(company_ids) - 1:
            full_story.append(PageBreak())

        kpis = get_company_kpi_trends(conn, company_id)
        na_count = sum(1 for k in kpis if k["arrow"] == "na")
        if na_count >= 4:
            na_heavy_companies.append((company_id, na_count))

    doc.build(full_story)
    conn.close()

    file_size_kb = OUTPUT_PATH.stat().st_size / 1024

    print("\n=== Day 35 Portfolio Summary ===")
    print(f"Companies included: {len(company_ids)}")
    print(f"Output: {OUTPUT_PATH}")
    print(f"File size: {file_size_kb:.1f} KB")
    print("\nCompanies with >=4/6 N/A trend arrows (thin data, worth spot-checking):")
    for cid, count in na_heavy_companies:
        print(f"  {cid}: {count}/6 N/A")


if __name__ == "__main__":
    main()
