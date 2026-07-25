-- =====================================================
-- Nifty 100 Financial Intelligence Platform
-- Sprint 1, Day 7 — Exploratory Queries
-- Run with: sqlite3 data/nifty100.db < exploratory_queries.sql
-- (or paste individual queries into DB Browser for SQLite / VS Code SQLite extension)
-- =====================================================

-- 1. Row counts across all 12 tables — quick health check against spec
-- expectations (companies=92, stock_prices=5520, market_cap=552 are exact
-- matches. The rest are lower than raw file counts due to documented
-- orphan-exclusion + dedup, see PROGRESS.md Day 5).
SELECT 'companies' AS table_name, COUNT(*) AS row_count FROM companies
UNION ALL SELECT 'sectors', COUNT(*) FROM sectors
UNION ALL SELECT 'profitandloss', COUNT(*) FROM profitandloss
UNION ALL SELECT 'balancesheet', COUNT(*) FROM balancesheet
UNION ALL SELECT 'cashflow', COUNT(*) FROM cashflow
UNION ALL SELECT 'analysis', COUNT(*) FROM analysis
UNION ALL SELECT 'documents', COUNT(*) FROM documents
UNION ALL SELECT 'prosandcons', COUNT(*) FROM prosandcons
UNION ALL SELECT 'stock_prices', COUNT(*) FROM stock_prices
UNION ALL SELECT 'market_cap', COUNT(*) FROM market_cap
UNION ALL SELECT 'financial_ratios', COUNT(*) FROM financial_ratios
UNION ALL SELECT 'peer_groups', COUNT(*) FROM peer_groups;


-- 2. NULL audit — profitandloss.operating_profit / opm_percentage by company.
-- Expect PNB (all years) and ADANIENSOL (some years) per Day 5/6 findings.
-- Any OTHER company appearing here is new and needs investigating.
SELECT
    company_id,
    SUM(CASE WHEN operating_profit IS NULL THEN 1 ELSE 0 END) AS missing_operating_profit,
    SUM(CASE WHEN opm_percentage IS NULL THEN 1 ELSE 0 END) AS missing_opm_percentage,
    COUNT(*) AS total_rows
FROM profitandloss
GROUP BY company_id
HAVING missing_operating_profit > 0 OR missing_opm_percentage > 0
ORDER BY missing_operating_profit DESC, missing_opm_percentage DESC;


-- 3. NULL audit — companies.face_value. Expect only TVSMOTOR per Day 5.
SELECT id, company_name, face_value, book_value
FROM companies
WHERE face_value IS NULL;


-- 4. Year coverage per company — flags combined P&L/BS/CF coverage < 5 years
-- (reproduces DQ-16 directly against the loaded DB, not the raw files).
-- Expect JIOFIN and SBIN per Day 6 findings.
SELECT * FROM (
    SELECT
        c.id AS company_id,
        (SELECT COUNT(DISTINCT year) FROM profitandloss WHERE company_id = c.id) AS pl_years,
        (SELECT COUNT(DISTINCT year) FROM balancesheet WHERE company_id = c.id) AS bs_years,
        (SELECT COUNT(DISTINCT year) FROM cashflow WHERE company_id = c.id) AS cf_years,
        MIN(
            (SELECT COUNT(DISTINCT year) FROM profitandloss WHERE company_id = c.id),
            (SELECT COUNT(DISTINCT year) FROM balancesheet WHERE company_id = c.id),
            (SELECT COUNT(DISTINCT year) FROM cashflow WHERE company_id = c.id)
        ) AS min_years
    FROM companies c
) WHERE min_years < 5
ORDER BY min_years;


-- 5. Generalised "balance sheet missing or starts later than P&L" detector.
-- This is the SBIN/HAL pattern from Day 6, generalised to ALL 92 companies
-- rather than relying on luck-of-the-random-sample to find it. Any company
-- appearing here that ISN'T SBIN or HAL is a NEW finding worth investigating
-- before Sprint 2 builds BS-anchored KPIs on top of it.
SELECT
    p.company_id,
    MIN(p.year) AS pl_start_year,
    (SELECT MIN(b.year) FROM balancesheet b WHERE b.company_id = p.company_id) AS bs_start_year
FROM profitandloss p
GROUP BY p.company_id
HAVING bs_start_year IS NULL OR bs_start_year > pl_start_year
ORDER BY bs_start_year IS NULL DESC, pl_start_year;


-- 6. Balance sheet balance check — flags any row where assets/liabilities
-- differ by more than 1% (DQ-04), reproduced directly against loaded data.
SELECT company_id, year, total_assets, total_liabilities,
       ROUND(ABS(total_assets - total_liabilities) * 100.0 / ABS(total_assets), 2) AS diff_pct
FROM balancesheet
WHERE total_assets != 0
  AND ABS(total_assets - total_liabilities) * 1.0 / ABS(total_assets) >= 0.01
ORDER BY diff_pct DESC;


-- 7. OPM cross-check — flags rows where source opm_percentage differs from
-- the computed value (operating_profit/sales*100) by more than 1 point (DQ-05).
-- Excludes NULL opm_percentage rows (PNB/ADANIENSOL — see query 2).
SELECT company_id, year, sales, operating_profit, opm_percentage,
       ROUND(operating_profit * 100.0 / sales, 2) AS computed_opm,
       ROUND(ABS(opm_percentage - (operating_profit * 100.0 / sales)), 2) AS diff
FROM profitandloss
WHERE sales != 0
  AND opm_percentage IS NOT NULL
  AND operating_profit IS NOT NULL
  AND ABS(opm_percentage - (operating_profit * 100.0 / sales)) >= 1.0
ORDER BY diff DESC;


-- 8. Sector distribution — count of companies per broad_sector.
-- Should sum to 92 and roughly match the spec's sector breakdown table.
SELECT broad_sector, COUNT(*) AS company_count
FROM sectors
GROUP BY broad_sector
ORDER BY company_count DESC;


-- 9. Peer group coverage — companies NOT in any peer group at all.
-- Spec notes ~46/92 coverage. This lists exactly which companies are excluded,
-- useful context for Sprint 4's Peer Comparison module so it isn't a surprise.
SELECT c.id, c.company_name
FROM companies c
LEFT JOIN peer_groups pg ON c.id = pg.company_id
WHERE pg.company_id IS NULL
ORDER BY c.id;


-- 10. Annual report (documents) coverage — companies with the fewest report
-- links on file. Helps anticipate which companies will show "report
-- unavailable" gaps in Module 11's Annual Reports dashboard screen.
SELECT company_id, COUNT(*) AS report_count
FROM documents
GROUP BY company_id
ORDER BY report_count ASC
LIMIT 15;