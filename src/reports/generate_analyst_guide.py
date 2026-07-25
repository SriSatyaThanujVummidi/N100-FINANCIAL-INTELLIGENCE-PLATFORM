"""
Day 44 -- Analyst Guide PDF Generator (Sprint 6, Module 12 documentation deliverable)

Builds docs/analyst_guide.pdf using ReportLab Platypus (same library already used for
tearsheets/sector reports, per project tech stack convention). Covers: screener usage,
dashboard screen-by-screen navigation, PDF tearsheet generation, API usage with curl
examples, and troubleshooting -- including the real bugs found and fixed this project
(SQLite cross-thread issue, sanity-bound masking, known data limitations), so this guide
is a genuine record of the system's actual behavior, not a generic template.
"""

from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
    Table,
    TableStyle,
    ListFlowable,
    ListItem,
)
from pypdf import PdfReader

OUTPUT_PATH = Path("docs/analyst_guide.pdf")
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

styles = getSampleStyleSheet()
styles.add(
    ParagraphStyle(
        name="H1Custom",
        parent=styles["Heading1"],
        spaceBefore=18,
        spaceAfter=10,
        textColor=colors.HexColor("#1a3a5c"),
    )
)
styles.add(
    ParagraphStyle(
        name="H2Custom",
        parent=styles["Heading2"],
        spaceBefore=14,
        spaceAfter=8,
        textColor=colors.HexColor("#2c5a8c"),
    )
)
styles.add(
    ParagraphStyle(name="BodyCustom", parent=styles["Normal"], spaceAfter=8, leading=15)
)
styles.add(
    ParagraphStyle(
        name="CodeBlock",
        parent=styles["Code"],
        backColor=colors.HexColor("#f0f0f0"),
        borderPadding=6,
        fontSize=9,
        leading=12,
        spaceAfter=10,
        spaceBefore=4,
    )
)
styles.add(
    ParagraphStyle(
        name="Caption",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.grey,
        spaceAfter=12,
    )
)

story = []

# ---------- Title Page ----------
story.append(Spacer(1, 2 * inch))
story.append(
    Paragraph(
        "Nifty 100 Financial Intelligence Platform",
        ParagraphStyle(
            name="Title1",
            parent=styles["Title"],
            fontSize=26,
            textColor=colors.HexColor("#1a3a5c"),
        ),
    )
)
story.append(Spacer(1, 0.2 * inch))
story.append(
    Paragraph(
        "Analyst Guide",
        ParagraphStyle(name="Title2", parent=styles["Title"], fontSize=18),
    )
)
story.append(Spacer(1, 0.5 * inch))
story.append(
    Paragraph(
        "Screener usage &middot; Dashboard navigation &middot; PDF reports &middot; REST API &middot; Troubleshooting",
        ParagraphStyle(
            name="Subtitle",
            parent=styles["Normal"],
            alignment=1,
            fontSize=11,
            textColor=colors.grey,
        ),
    )
)
story.append(Spacer(1, 1.5 * inch))
story.append(
    Paragraph("Sprint 6, Day 44 &mdash; Documentation Deliverable", styles["Caption"])
)
story.append(PageBreak())

# ---------- Table of Contents ----------
story.append(Paragraph("Table of Contents", styles["H1Custom"]))
toc_items = [
    "1. Getting Started",
    "2. Using the Investment Screener",
    "3. Dashboard Screen-by-Screen Guide",
    "4. Generating PDF Tearsheets",
    "5. Calling the REST API",
    "6. Full API Endpoint Reference",
    "7. Troubleshooting Common Issues",
    "8. Known Data Limitations (Read Before Interpreting Results)",
]
story.append(
    ListFlowable(
        [ListItem(Paragraph(t, styles["BodyCustom"])) for t in toc_items],
        bulletType="bullet",
    )
)
story.append(PageBreak())

# ---------- 1. Getting Started ----------
story.append(Paragraph("1. Getting Started", styles["H1Custom"]))
story.append(
    Paragraph(
        "This platform analyzes 92 Nifty 100 companies using data loaded into a local SQLite "
        "database (data/nifty100.db). All commands below assume a Windows 11 / PowerShell "
        "environment with the project's virtual environment (.venv) activated.",
        styles["BodyCustom"],
    )
)

story.append(Paragraph("Activate the environment:", styles["H2Custom"]))
story.append(Paragraph(".\\.venv\\Scripts\\Activate.ps1", styles["CodeBlock"]))

story.append(
    Paragraph(
        "Rebuild the database from source Excel files (if needed):", styles["H2Custom"]
    )
)
story.append(Paragraph("python -m src.etl.full_load", styles["CodeBlock"]))

story.append(
    Paragraph(
        "Recompute all financial ratios (after any KPI formula change):",
        styles["H2Custom"],
    )
)
story.append(
    Paragraph("python -m src.analytics.populate_financial_ratios", styles["CodeBlock"])
)

story.append(Paragraph("Run the full test suite:", styles["H2Custom"]))
story.append(
    Paragraph(
        "python -m pytest tests/ --html=reports/pytest_report.html --self-contained-html",
        styles["CodeBlock"],
    )
)
story.append(
    Paragraph(
        "Note: use <b>python -m ...</b> for every module invocation, not <b>py -m ...</b> &mdash; "
        "the <b>py</b> launcher can point to a stale interpreter path independent of the active "
        "venv on some machines. If <b>python</b> itself fails to resolve, close and reopen the "
        "terminal, reactivate the venv, and try again before troubleshooting further.",
        styles["BodyCustom"],
    )
)
story.append(PageBreak())

# ---------- 2. Using the Screener ----------
story.append(Paragraph("2. Using the Investment Screener", styles["H1Custom"]))
story.append(
    Paragraph(
        "The screener is available two ways: inside the Streamlit dashboard (Screener screen, "
        "sidebar sliders) and via the REST API (<b>GET /api/v1/screener</b>). Both use the same "
        "underlying logic and return identical results for the same filter values &mdash; this "
        "was explicitly verified (Sprint 6 Day 42 integration test).",
        styles["BodyCustom"],
    )
)

story.append(Paragraph("Six preset screeners are available:", styles["H2Custom"]))
preset_data = [
    ["Preset", "Filters", "Typical count"],
    [
        "Quality Compounder",
        "ROE>15%, D/E<1 (Financials exempt), FCF>0, Rev CAGR 5yr>10%",
        "~21",
    ],
    ["Value Pick", "P/E<50, P/B<5", "~14"],
    ["Growth Accelerator", "PAT CAGR 5yr>20%, Rev CAGR 5yr>15%, D/E<2", "~19"],
    ["Dividend Champion", "Dividend Yield>3.5%, Payout<80%, FCF>0", "~14"],
    ["Debt-Free Blue Chip", "D/E<0.1, Financials excluded entirely, ROE>12%", "~19"],
    ["Turnaround Watch", "Revenue CAGR 3yr>18%, FCF improving, D/E declining", "~12"],
]
t = Table(preset_data, colWidths=[1.6 * inch, 3.3 * inch, 1.0 * inch])
t.setStyle(
    TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3a5c")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            (
                "ROWBACKGROUNDS",
                (0, 1),
                (-1, -1),
                [colors.white, colors.HexColor("#f0f4f8")],
            ),
        ]
    )
)
story.append(t)
story.append(Spacer(1, 10))
story.append(
    Paragraph(
        "<b>Important:</b> preset thresholds were recalibrated from the original project spec "
        "using real data distributions (e.g. Value Pick's P/E threshold was raised from 20 to 50, "
        "since Nifty 100 large-caps trade at higher multiples than the spec assumed). See "
        "docs/PROGRESS.md Sprint 3 Day 16 for the full rationale on each recalibration.",
        styles["BodyCustom"],
    )
)

story.append(Paragraph("Custom filters:", styles["H2Custom"]))
story.append(
    Paragraph(
        "Beyond the presets, any combination of filters can be built via the dashboard's sidebar "
        "sliders (Financial Screener screen) or the API's query parameters: min_roe, max_de, "
        "min_fcf, sector, min_rev_cagr_5yr, min_pat_cagr_5yr, max_pe.",
        styles["BodyCustom"],
    )
)
story.append(PageBreak())

# ---------- 3. Dashboard Screens ----------
story.append(Paragraph("3. Dashboard Screen-by-Screen Guide", styles["H1Custom"]))
story.append(
    Paragraph(
        "Start the dashboard with: <b>streamlit run src/dashboard/app.py</b> &mdash; it opens at "
        "http://localhost:8501. All 8 screens are listed in the left sidebar.",
        styles["BodyCustom"],
    )
)

screens = [
    (
        "Home / Overview",
        "Summary KPI tiles (avg ROE, median P/E), sector donut chart, top-5 "
        "composite score table. Sector filter chips and year selector at the top.",
    ),
    (
        "Company Profile",
        "Search by ticker or company name. Shows a company card, 6 KPI tiles, "
        "10-year revenue/profit chart, ROE/ROCE trend line, and pros/cons badges.",
    ),
    (
        "Financial Screener",
        "10 metric sliders in the sidebar, live-updating results table, "
        "6 preset buttons, and a CSV download button.",
    ),
    (
        "Peer Comparison",
        "Select a peer group from the dropdown to see a radar chart plus a "
        "side-by-side comparison table with the group's designated benchmark company highlighted.",
    ),
    (
        "Trend Analysis",
        "Search a company, select up to 3 metrics to overlay on a 10-year line "
        "chart with year-over-year percentage change annotations.",
    ),
    (
        "Sector Analysis",
        "Select a sector to see a bubble chart (revenue vs. ROE, sized by "
        "market cap) and a bar chart of sector median KPIs.",
    ),
    (
        "Capital Allocation Map",
        "Treemap of all 92 companies grouped into 8 capital allocation "
        "patterns (Reinvestor, Shareholder Returns, Distress Signal, etc.). Click a pattern to "
        "drill into the company list.",
    ),
    (
        "Annual Reports",
        "Search a company to see clickable links to its historical annual "
        "report PDFs on BSE India. A red badge marks years with no available report.",
    ),
]
for name, desc in screens:
    story.append(Paragraph(name, styles["H2Custom"]))
    story.append(Paragraph(desc, styles["BodyCustom"]))

story.append(
    Paragraph(
        "Note: the Sector Analysis screen shows 10 sectors, not 11 as an earlier project "
        "specification assumed &mdash; the underlying sectors table genuinely contains only 10 "
        "distinct values. This is called out directly in-app on that screen.",
        styles["BodyCustom"],
    )
)
story.append(PageBreak())

# ---------- 4. PDF Tearsheets ----------
story.append(Paragraph("4. Generating PDF Tearsheets", styles["H1Custom"]))
story.append(
    Paragraph(
        "Each of the 92 companies has a 2-page PDF tearsheet: KPI tiles, revenue/profit and "
        "ROE/ROCE charts on page 1; balance sheet composition, cash flow waterfall, and "
        "pros/cons on page 2.",
        styles["BodyCustom"],
    )
)

story.append(Paragraph("Generate a single company's tearsheet:", styles["H2Custom"]))
story.append(
    Paragraph("python -m src.reports.tearsheet --ticker TCS", styles["CodeBlock"])
)

story.append(Paragraph("Generate the full batch (all 92):", styles["H2Custom"]))
story.append(Paragraph("python -m src.reports.batch_tearsheets", styles["CodeBlock"]))
story.append(
    Paragraph(
        "Output goes to reports/tearsheets/&lt;TICKER&gt;_tearsheet.pdf. One company (JIOFIN) is "
        "deliberately skipped &mdash; it has only 2 years of trading history, below the 3-year "
        "minimum needed for a meaningful trend chart. This is logged to "
        "output/skipped_tearsheets.csv, not a failure.",
        styles["BodyCustom"],
    )
)

story.append(Paragraph("Also available:", styles["H2Custom"]))
story.append(
    Paragraph(
        "python -m src.reports.sector_report &nbsp;&nbsp;(11-sector median KPI reports; note: "
        "spec says 11, real data produces 10)<br/>"
        "python -m src.reports.portfolio_summary &nbsp;&nbsp;(all 92 companies, 1 page each)",
        styles["CodeBlock"],
    )
)
story.append(PageBreak())

# ---------- 5. API ----------
story.append(Paragraph("5. Calling the REST API", styles["H1Custom"]))
story.append(
    Paragraph(
        "Start the API with: <b>python -m uvicorn src.api.main:app --port 8000</b> &mdash; "
        "interactive OpenAPI docs are then available at http://localhost:8000/docs.",
        styles["BodyCustom"],
    )
)

api_examples = [
    ("Health check", "curl.exe http://localhost:8000/api/v1/health"),
    (
        "List companies in a sector",
        'curl.exe "http://localhost:8000/api/v1/companies?sector=Information%20Technology"',
    ),
    ("Full company profile", "curl.exe http://localhost:8000/api/v1/companies/TCS"),
    (
        "P&L history with year filter",
        'curl.exe "http://localhost:8000/api/v1/companies/TCS/pl?from_year=2022-03&to_year=2024-03"',
    ),
    (
        "Run the screener",
        'curl.exe "http://localhost:8000/api/v1/screener?min_roe=15&max_de=1&sector=Information%20Technology"',
    ),
    (
        "Peer group comparison",
        'curl.exe "http://localhost:8000/api/v1/peers/IT%20Services"',
    ),
    (
        "Download a tearsheet PDF",
        "curl.exe -o tcs_tearsheet.pdf http://localhost:8000/api/v1/companies/TCS/tearsheet",
    ),
    (
        "Portfolio-wide statistics",
        "curl.exe http://localhost:8000/api/v1/portfolio/stats",
    ),
]
for label, cmd in api_examples:
    story.append(Paragraph(label, styles["H2Custom"]))
    story.append(Paragraph(cmd, styles["CodeBlock"]))

story.append(
    Paragraph(
        "<b>Data quality flags on the API:</b> a small number of companies (HAL, BEL, INDIGO, "
        "ICICIPRULI, HDFCLIFE) have ROE/ROCE/ROA values so extreme they are almost certainly "
        "data artifacts, not real performance (e.g. one company's raw ROE computes to over "
        "3,800%). Rather than silently hiding these, the API returns "
        "<b>null</b> for the field plus an explicit sibling field, e.g. "
        '<b>return_on_equity_pct_quality_flag: "excluded_sanity_bound_exceeded"</b>, so API '
        "consumers know data exists but was excluded, rather than mistaking it for a missing "
        "value.",
        styles["BodyCustom"],
    )
)
story.append(PageBreak())

# ---------- 6. Full API Endpoint Reference ----------
story.append(Paragraph("6. Full API Endpoint Reference", styles["H1Custom"]))
story.append(
    Paragraph(
        "All 16 endpoints, mounted under the /api/v1 prefix.", styles["BodyCustom"]
    )
)
endpoint_data = [
    ["Method", "Endpoint", "Description"],
    ["GET", "/health", "Server status, DB row counts, uptime"],
    [
        "GET",
        "/companies",
        "List all 92 companies; filters: sector, market_cap_category, search",
    ],
    ["GET", "/companies/{ticker}", "Full company profile incl. latest KPIs"],
    ["GET", "/companies/{ticker}/pl", "P&L history; filters: from_year, to_year"],
    ["GET", "/companies/{ticker}/bs", "Balance sheet history; same filters"],
    ["GET", "/companies/{ticker}/cashflow", "Cash flow history; same filters"],
    [
        "GET",
        "/companies/{ticker}/ratios",
        "All computed KPIs per year; optional single year",
    ],
    [
        "GET",
        "/companies/{ticker}/tearsheet",
        "Binary PDF download of the 2-page tearsheet",
    ],
    ["GET", "/companies/{ticker}/documents", "Annual report links with validity flag"],
    [
        "GET",
        "/companies/{ticker}/peers/compare",
        "Radar data: company vs. peer group vs. benchmark",
    ],
    ["GET", "/screener", "Ranked results; 7 filter params; 400 on invalid values"],
    [
        "GET",
        "/sectors",
        "All sectors with company_count, median_roe, median_pe, median_de",
    ],
    ["GET", "/sectors/{sector}/companies", "Companies in a sector with latest KPIs"],
    [
        "GET",
        "/peers/{group_name}",
        "Peer group members with percentile rank per metric",
    ],
    ["GET", "/market-cap/{ticker}", "Historical P/E, P/B, EV/EBITDA, dividend yield"],
    ["GET", "/portfolio/stats", "P10-P90 percentile table across all core KPIs"],
]
t2 = Table(endpoint_data, colWidths=[0.6 * inch, 2.3 * inch, 3.0 * inch])
t2.setStyle(
    TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3a5c")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            (
                "ROWBACKGROUNDS",
                (0, 1),
                (-1, -1),
                [colors.white, colors.HexColor("#f0f4f8")],
            ),
        ]
    )
)
story.append(t2)
story.append(Spacer(1, 10))
story.append(
    Paragraph(
        "Interactive documentation with request/response schemas for every endpoint is "
        "auto-generated at http://localhost:8000/docs whenever the API server is running.",
        styles["BodyCustom"],
    )
)
story.append(PageBreak())

# ---------- 7. Troubleshooting ----------
story.append(Paragraph("7. Troubleshooting Common Issues", styles["H1Custom"]))

issues = [
    (
        '"py" command not found or points to a broken interpreter',
        "Use <b>python -m ...</b> instead of <b>py -m ...</b> for every command in this guide. "
        "The <b>py</b> launcher's registered interpreter path can go stale independently of the "
        "project's own .venv, especially after a Python reinstall.",
    ),
    (
        "ModuleNotFoundError when running the full test suite together",
        "A small number of older test files use <b>from analytics.X import ...</b> while newer "
        "files use <b>from src.analytics.X import ...</b>. These files pass individually "
        "(<b>pytest tests/kpi/</b>) but fail to collect when the entire tests/ tree runs "
        "together. Workaround: run <b>pytest tests/ --continue-on-collection-errors</b>, which "
        "correctly reports all other tests' pass/fail status and lists the affected files "
        "separately as collection errors, not test failures.",
    ),
    (
        "API returns HTTP 500 under concurrent load",
        "Fixed as of Sprint 6 Day 43: src/api/db.py's database connection now uses "
        "<b>check_same_thread=False</b>. If you see "
        '"SQLite objects created in a thread can only be used in that same thread", confirm '
        "this fix is present in your checkout.",
    ),
    (
        'A company shows blank or "N/A" for ROE, ROCE, or D/E',
        "Check whether the company is SBIN (zero balance sheet rows &mdash; a genuine source "
        "data gap, not a bug) or one of HAL/BEL/INDIGO/ICICIPRULI/HDFCLIFE (values excluded by "
        "the sanity-bound check because they are implausibly extreme). Both cases are "
        "intentional, documented data-quality handling, not application errors.",
    ),
    (
        "Dashboard chart looks empty or shows a warning for a metric",
        "Some companies have long stretches of missing data for a specific metric across all "
        "reported years (SBIN's ROE/ROCE/D/E, for example). The dashboard shows an explicit "
        '"no plottable data" message in this case rather than a blank or broken chart.',
    ),
    (
        "Report file smaller than expected",
        "A company missing one or more chart inputs (e.g. SBIN's balance sheet chart, or the "
        "sanity-bound-masked companies' ROE/ROCE chart) will produce a correctly smaller PDF "
        "with 3 of 4 charts instead of 4 &mdash; this is expected given the known data gap, not "
        "a rendering failure.",
    ),
]
for title, body in issues:
    story.append(Paragraph(title, styles["H2Custom"]))
    story.append(Paragraph(body, styles["BodyCustom"]))
story.append(PageBreak())

# ---------- 8. Known Data Limitations ----------
story.append(
    Paragraph(
        "8. Known Data Limitations (Read Before Interpreting Results)",
        styles["H1Custom"],
    )
)
story.append(
    Paragraph(
        "This platform is built directly against the real source data, including its "
        "imperfections. The following are established, investigated findings &mdash; not "
        "unexplained bugs &mdash; documented in full in docs/PROGRESS.md.",
        styles["BodyCustom"],
    )
)

limitations = [
    "SBIN has zero rows in the balance sheet source file. All balance-sheet-derived metrics "
    "(ROE, ROCE, D/E, Asset Turnover, Book Value/Share) are unavailable for SBIN specifically.",
    "HAL's balance sheet equity figures are roughly 147x too small relative to independently "
    "sourced figures, for reasons not fully diagnosed. This produces implausible ROE/ROCE; "
    "these fields are excluded (not fabricated) wherever HAL appears.",
    "BEL, INDIGO, ICICIPRULI, and HDFCLIFE show the same category of implausible ROE/ROCE "
    "for similar near-zero-equity reasons; all are excluded the same way.",
    "The sectors table contains 10 distinct broad sectors, not the 11 originally specified. "
    "Root cause not diagnosed; the platform reports the real 10.",
    "Operating margin should always be read from the computed value (sales minus expenses "
    "divided by sales), never from the source file's own opm_percentage field, which "
    "diverges from the computed value for a number of companies, including several where it "
    "appears to hold a raw currency figure rather than a percentage.",
    "Financial-sector companies (banks, NBFCs, insurers) are exempted from several "
    "cross-sector rules (high D/E flags, ROCE benchmark bands, a cash-flow distress rule) "
    "because high leverage and unusual cash flow shapes are structurally normal for lenders, "
    "not warning signs.",
]
story.append(
    ListFlowable(
        [ListItem(Paragraph(item, styles["BodyCustom"])) for item in limitations],
        bulletType="bullet",
    )
)

story.append(Spacer(1, 20))
story.append(
    Paragraph(
        "For the complete, day-by-day record of every data-quality finding and design decision "
        "behind this platform, see docs/PROGRESS.md.",
        styles["Caption"],
    )
)

doc = SimpleDocTemplate(
    str(OUTPUT_PATH),
    pagesize=letter,
    topMargin=0.75 * inch,
    bottomMargin=0.75 * inch,
    leftMargin=0.85 * inch,
    rightMargin=0.85 * inch,
)
doc.build(story)

print(f"Generated: {OUTPUT_PATH}")
reader = PdfReader(str(OUTPUT_PATH))
print(f"Page count: {len(reader.pages)}")
