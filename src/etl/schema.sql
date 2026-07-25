-- =====================================================
-- Nifty 100 Financial Intelligence Platform
-- SQLite Schema — Day 4, Sprint 1
-- 12 tables (one per real source Excel file)
-- NOTE: PRAGMA foreign_keys is a per-connection setting, not stored
-- in the schema file — it's turned on in db.py at connection time.
-- =====================================================

-- 1. companies — master reference table
CREATE TABLE IF NOT EXISTS companies (
    id                  TEXT PRIMARY KEY,
    company_logo        TEXT,
    company_name        TEXT NOT NULL,
    chart_link          TEXT,
    about_company       TEXT,
    website             TEXT,
    nse_profile         TEXT,
    bse_profile         TEXT,
    face_value          REAL,
    book_value          REAL,
    roce_percentage     REAL,
    roe_percentage      REAL
);

-- 2. profitandloss — composite PK (company_id, year) per spec dataset catalogue
CREATE TABLE IF NOT EXISTS profitandloss (
    source_id           INTEGER,            -- original 'id' col, kept for traceability only
    company_id          TEXT NOT NULL,
    year                TEXT NOT NULL,       -- normalised 'YYYY-MM' via normalize_year()
    sales                REAL NOT NULL,
    expenses             REAL NOT NULL,
    operating_profit      REAL,
    opm_percentage         REAL,
    other_income            REAL,
    interest                 REAL,
    depreciation               REAL,
    profit_before_tax           REAL,
    tax_percentage                REAL,
    net_profit                     REAL,
    eps                              REAL,
    dividend_payout                    REAL,
    PRIMARY KEY (company_id, year),
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

-- 3. balancesheet — composite PK (company_id, year)
CREATE TABLE IF NOT EXISTS balancesheet (
    source_id            INTEGER,
    company_id           TEXT NOT NULL,
    year                  TEXT NOT NULL,
    equity_capital          REAL NOT NULL,
    reserves                 REAL,
    borrowings                 REAL,
    other_liabilities            REAL,
    total_liabilities              REAL NOT NULL,
    fixed_assets                     REAL,
    cwip                               REAL,
    investments                          REAL,
    other_asset                            REAL,
    total_assets                              REAL NOT NULL,
    PRIMARY KEY (company_id, year),
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

-- 4. cashflow — composite PK (company_id, year)
CREATE TABLE IF NOT EXISTS cashflow (
    source_id          INTEGER,
    company_id         TEXT NOT NULL,
    year                TEXT NOT NULL,
    operating_activity    REAL,
    investing_activity      REAL,
    financing_activity        REAL,
    net_cash_flow                REAL,
    PRIMARY KEY (company_id, year),
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

-- 5. analysis — partial coverage (~8 companies), 1:1 with companies
CREATE TABLE IF NOT EXISTS analysis (
    id                          INTEGER PRIMARY KEY,
    company_id                 TEXT NOT NULL,
    compounded_sales_growth      TEXT,
    compounded_profit_growth       TEXT,
    stock_price_cagr                 TEXT,
    roe                                TEXT,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

-- 6. documents — composite PK (company_id, report_year)
-- NOTE: source column was 'Year' (capital Y) and 'Annual_Report' — renamed on insert
CREATE TABLE IF NOT EXISTS documents (
    source_id              INTEGER,
    company_id              TEXT NOT NULL,
    report_year                INTEGER NOT NULL,
    annual_report_url             TEXT,
    PRIMARY KEY (company_id, report_year),
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

-- 7. prosandcons — partial coverage, multiple rows per company allowed, PK = source id
CREATE TABLE IF NOT EXISTS prosandcons (
    id                INTEGER PRIMARY KEY,
    company_id          TEXT NOT NULL,
    pros                  TEXT,
    cons                    TEXT,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

-- 8. sectors — 1:1 with companies
CREATE TABLE IF NOT EXISTS sectors (
    company_id               TEXT PRIMARY KEY,
    broad_sector                TEXT NOT NULL,
    sub_sector                    TEXT NOT NULL,
    index_weight_pct                 REAL,
    market_cap_category                 TEXT,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

-- 9. stock_prices — composite PK (company_id, date), monthly OHLCV
CREATE TABLE IF NOT EXISTS stock_prices (
    company_id            TEXT NOT NULL,
    date                     TEXT NOT NULL,      -- 'YYYY-MM-DD'
    open_price                 REAL,
    high_price                    REAL,
    low_price                       REAL,
    close_price                       REAL,
    volume                               INTEGER,
    adjusted_close                         REAL,
    PRIMARY KEY (company_id, date),
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

-- 10. market_cap — composite PK (company_id, year)
CREATE TABLE IF NOT EXISTS market_cap (
    company_id               TEXT NOT NULL,
    year                        INTEGER NOT NULL,
    market_cap_crore               REAL,
    enterprise_value_crore            REAL,
    pe_ratio                             REAL,
    pb_ratio                               REAL,
    ev_ebitda                                 REAL,
    dividend_yield_pct                           REAL,
    PRIMARY KEY (company_id, year),
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

-- 11. financial_ratios — pre-computed KPI table, composite PK (company_id, year)
-- This table gets re-populated properly in Sprint 2 (Module 2); schema only for now.
CREATE TABLE IF NOT EXISTS financial_ratios (
    company_id                       TEXT NOT NULL,
    year                                TEXT NOT NULL,
    net_profit_margin_pct                 REAL,
    operating_profit_margin_pct              REAL,
    return_on_equity_pct                        REAL,
    debt_to_equity                                 REAL,
    interest_coverage                                 REAL,
    asset_turnover                                       REAL,
    free_cash_flow_cr                                       REAL,
    capex_cr                                                   REAL,
    earnings_per_share                                            REAL,
    book_value_per_share                                            REAL,
    dividend_payout_ratio_pct                                          REAL,
    total_debt_cr                                                         REAL,
    cash_from_operations_cr                                                  REAL,
    PRIMARY KEY (company_id, year),
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

-- 12. peer_groups — REAL structure (one row per company per group), NOT comma-separated
CREATE TABLE IF NOT EXISTS peer_groups (
    id                    INTEGER PRIMARY KEY,
    peer_group_name          TEXT NOT NULL,
    company_id                  TEXT NOT NULL,
    is_benchmark                   INTEGER NOT NULL DEFAULT 0,  -- 0/1 boolean
    UNIQUE (peer_group_name, company_id),
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

-- Helpful indexes for the Screener / Dashboard / Peer modules (Sprints 3–5)
CREATE INDEX IF NOT EXISTS idx_pl_company ON profitandloss(company_id);
CREATE INDEX IF NOT EXISTS idx_bs_company ON balancesheet(company_id);
CREATE INDEX IF NOT EXISTS idx_cf_company ON cashflow(company_id);
CREATE INDEX IF NOT EXISTS idx_docs_company ON documents(company_id);
CREATE INDEX IF NOT EXISTS idx_prosandcons_company ON prosandcons(company_id);
CREATE INDEX IF NOT EXISTS idx_stockprices_company ON stock_prices(company_id);
CREATE INDEX IF NOT EXISTS idx_marketcap_company ON market_cap(company_id);
CREATE INDEX IF NOT EXISTS idx_ratios_company ON financial_ratios(company_id);
CREATE INDEX IF NOT EXISTS idx_peergroups_company ON peer_groups(company_id);