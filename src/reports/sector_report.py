"""
src/reports/sector_report.py

Day 34 — Sprint 5, Module 8 (Batch Report Generation, part 2)
One PDF per broad_sector (11 sectors, per Day 22/25's finding — spec's
"11 sectors" claim vs the real 10-distinct-value table is a known,
already-documented discrepancy; this generates one PDF per DISTINCT
value actually present, whatever that count turns out to be today).

Each sector PDF: a summary page with sector median KPIs, followed by a
table listing every company in that sector with 8 key metrics.

Sanity-bound masking (Day 13/17/18, ±500%) applied before computing
medians, so HAL/BEL/INDIGO/ICICIPRULI/HDFCLIFE-style artifacts can't
skew a sector's benchmark — same principle as Day 17's sector-relative
composite score and Day 23's dashboard averages.
"""

import logging
import sqlite3
import statistics
from pathlib import Path
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "data" / "nifty100.db"
SECTOR_DIR = PROJECT_ROOT / "reports" / "sector"

NAVY = colors.HexColor("#1F4E78")
LIGHT_GREY = colors.HexColor("#F2F2F2")
SANITY_BOUND_PCT = 500.0

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

PAGE_W, PAGE_H = A4
MARGIN = 1.5 * cm
USABLE_WIDTH = PAGE_W - 2 * MARGIN


def is_implausible_pct(value: Optional[float]) -> bool:
    """Is implausible pct."""
    return value is not None and abs(value) > SANITY_BOUND_PCT


def get_connection() -> sqlite3.Connection:
    """Get connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_sector_companies(conn: sqlite3.Connection, sector: str) -> list[dict]:
    """For every company in this sector, latest financial_ratios row
    plus company name. Sanity-masked ROE/ROCE per project convention."""
    company_ids = [
        r["company_id"]
        for r in conn.execute(
            "SELECT company_id FROM sectors WHERE broad_sector = ? ORDER BY company_id",
            (sector,),
        )
    ]

    rows = []
    for cid in company_ids:
        name_row = conn.execute(
            "SELECT company_name FROM companies WHERE id = ?", (cid,)
        ).fetchone()
        latest = conn.execute(
            "SELECT * FROM financial_ratios WHERE company_id = ? ORDER BY year DESC LIMIT 1",
            (cid,),
        ).fetchone()

        if name_row is None:
            continue  # FK-excluded ticker, shouldn't happen since sectors joins on companies

        row = {
            "company_id": cid,
            "company_name": name_row["company_name"],
            "roe": None,
            "roce": None,
            "de": None,
            "opm": None,
            "revenue_cagr_5yr": None,
            "npm": None,
            "fcf": None,
            "eps_cagr_5yr": None,
        }
        if latest is not None:
            roe = latest["return_on_equity_pct"]
            roce = latest["return_on_capital_employed_pct"]
            row["roe"] = None if is_implausible_pct(roe) else roe
            row["roce"] = None if is_implausible_pct(roce) else roce
            row["de"] = latest["debt_to_equity"]
            row["opm"] = latest["operating_profit_margin_pct"]
            row["revenue_cagr_5yr"] = latest["revenue_cagr_5yr"]
            row["npm"] = latest["net_profit_margin_pct"]
            row["fcf"] = latest["free_cash_flow_cr"]
            row["eps_cagr_5yr"] = latest["eps_cagr_5yr"]

        rows.append(row)

    return rows


def compute_medians(companies: list[dict]) -> dict:
    """Compute medians."""

    def median_of(field):
        """Median of."""
        vals = [c[field] for c in companies if c[field] is not None]
        return round(statistics.median(vals), 2) if vals else None

    return {
        "roe": median_of("roe"),
        "roce": median_of("roce"),
        "de": median_of("de"),
        "opm": median_of("opm"),
        "revenue_cagr_5yr": median_of("revenue_cagr_5yr"),
        "npm": median_of("npm"),
        "fcf": median_of("fcf"),
        "eps_cagr_5yr": median_of("eps_cagr_5yr"),
    }


def fmt(val, suffix="%", precision=1):
    """Fmt."""
    if val is None:
        return "N/A"
    if suffix == "x":
        return f"{val:.2f}x"
    if suffix == "Cr":
        return f"Rs {val:,.0f} Cr"
    return f"{val:.{precision}f}{suffix}"


def build_sector_pdf(conn: sqlite3.Connection, sector: str, output_path: Path) -> dict:
    """Build sector pdf."""
    companies = get_sector_companies(conn, sector)
    medians = compute_medians(companies)

    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle(
        "sector_title",
        parent=styles["Normal"],
        fontSize=18,
        textColor=colors.white,
        fontName="Helvetica-Bold",
    )
    header = Table(
        [
            [Paragraph(f"{sector} Sector Report", title_style)],
            [
                Paragraph(
                    f"{len(companies)} companies",
                    ParagraphStyle(
                        "sub",
                        parent=styles["Normal"],
                        fontSize=10,
                        textColor=colors.white,
                    ),
                )
            ],
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
    story.append(Spacer(1, 12))

    story.append(Paragraph("Sector Median KPIs", styles["Heading2"]))
    median_data = [
        ["Metric", "Median"],
        ["ROE", fmt(medians["roe"])],
        ["ROCE", fmt(medians["roce"])],
        ["D/E", fmt(medians["de"], suffix="x")],
        ["OPM", fmt(medians["opm"])],
        ["Revenue CAGR 5yr", fmt(medians["revenue_cagr_5yr"])],
        ["Net Profit Margin", fmt(medians["npm"])],
        ["Free Cash Flow", fmt(medians["fcf"], suffix="Cr")],
        ["EPS CAGR 5yr", fmt(medians["eps_cagr_5yr"])],
    ]
    median_table = Table(
        median_data, colWidths=[USABLE_WIDTH * 0.5, USABLE_WIDTH * 0.5]
    )
    median_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GREY]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(median_table)
    story.append(Spacer(1, 16))

    story.append(Paragraph("Companies in Sector", styles["Heading2"]))
    para_style = ParagraphStyle(
        "cell", parent=styles["Normal"], fontSize=7.5, leading=9
    )
    company_header = [
        "Company",
        "ROE",
        "ROCE",
        "D/E",
        "OPM",
        "Rev CAGR 5yr",
        "NPM",
        "FCF (Cr)",
    ]
    company_data = [company_header]
    for c in companies:
        # Paragraph wraps long company names automatically -> WORDWRAP
        company_data.append(
            [
                Paragraph(f"{c['company_name']} ({c['company_id']})", para_style),
                fmt(c["roe"]),
                fmt(c["roce"]),
                fmt(c["de"], suffix="x"),
                fmt(c["opm"]),
                fmt(c["revenue_cagr_5yr"]),
                fmt(c["npm"]),
                fmt(c["fcf"], suffix="Cr", precision=0),
            ]
        )

    col_widths = [USABLE_WIDTH * 0.30] + [USABLE_WIDTH * 0.10] * 6
    company_table = Table(company_data, colWidths=col_widths, repeatRows=1)
    company_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 8),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GREY]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTSIZE", (0, 1), (-1, -1), 7.5),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(company_table)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
    )
    doc.build(story)

    return {
        "sector": sector,
        "company_count": len(companies),
        "file_size_kb": round(output_path.stat().st_size / 1024, 1),
    }


def main() -> None:
    """Main."""
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found at {DB_PATH}")

    SECTOR_DIR.mkdir(parents=True, exist_ok=True)
    conn = get_connection()

    sectors = sorted(
        r["broad_sector"]
        for r in conn.execute("SELECT DISTINCT broad_sector FROM sectors")
    )
    logger.info("Found %d distinct sectors in the sectors table", len(sectors))

    results = []
    for sector in sectors:
        safe_name = sector.replace("/", "-").replace(" ", "_")
        output_path = SECTOR_DIR / f"{safe_name}_report.pdf"
        try:
            diag = build_sector_pdf(conn, sector, output_path)
            diag["status"] = "OK"
        except Exception as e:
            diag = {"sector": sector, "status": f"FAILED: {e}"}
        results.append(diag)

    conn.close()

    total_companies_covered = sum(r.get("company_count", 0) for r in results)

    print("\n=== Day 34 Sector Report Summary ===")
    print(f"Sectors found in DB: {len(sectors)}")
    for r in results:
        if r["status"] == "OK":
            print(
                f"  {r['sector']:30s} {r['company_count']:3d} companies  {r['file_size_kb']:.1f} KB"
            )
        else:
            print(f"  {r['sector']:30s} {r['status']}")
    print(
        f"\nTotal companies covered across all sector reports: {total_companies_covered}"
    )


if __name__ == "__main__":
    main()
