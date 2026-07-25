-- exploratory_queries.sql
-- Sprint 1, Day 7 deliverable (originally left "Not started" through Sprint 1's own retro;
-- completed here at Day 45 final sign-off rather than left as a permanent gap).
-- 10 queries: row counts, null checks, and year coverage per company across the real
-- 92-company nifty100.db.

-- 1. Row counts across all 12 tables
SELECT 'companies' AS table_name, COUNT(*) AS row_count FROM companies
UNION ALL SELECT 'profitandloss', COUNT(*) FROM profitandloss
UNION ALL SELECT 'balancesheet', COUNT(*) FROM balancesheet
UNION ALL SELECT 'cashflow', COUNT(*) FROM cashflow
UNION ALL SELECT 'analysis', COUNT(*) FROM analysis
UNION ALL SELECT 'documents', COUNT(*) FROM documents
UNION ALL SELECT 'prosandcons', COUNT(*) FROM prosandcons
UNION ALL SELECT 'sectors', COUNT(*) FROM sectors
UNION ALL SELECT 'stock_prices', COUNT(*) FROM stock_prices
UNION ALL SELECT 'market_cap', COUNT(*) FROM market_cap
UNION ALL SELECT 'financial_ratios', COUNT(*) FROM financial_ratios
UNION ALL SELECT 'peer_groups', COUNT(*) FROM peer_groups;

-- 2. Null check: sales, operating_profit, net_profit across profitandloss
SELECT
    SUM(CASE WHEN sales IS NULL THEN 1 ELSE 0 END) AS null_sales,
    SUM(CASE WHEN operating_profit IS NULL THEN 1 ELSE 0 END) AS null_operating_profit,
    SUM(CASE WHEN net_profit IS NULL THEN 1 ELSE 0 END) AS null_net_profit,
    COUNT(*) AS total_rows
FROM profitandloss;

-- 3. Null check: borrowings, reserves, total_assets across balancesheet
SELECT
    SUM(CASE WHEN borrowings IS NULL THEN 1 ELSE 0 END) AS null_borrowings,
    SUM(CASE WHEN reserves IS NULL THEN 1 ELSE 0 END) AS null_reserves,
    SUM(CASE WHEN total_assets IS NULL THEN 1 ELSE 0 END) AS null_total_assets,
    COUNT(*) AS total_rows
FROM balancesheet;

-- 4. Year coverage per company: P&L years reported
SELECT company_id, COUNT(DISTINCT year) AS pl_years, MIN(year) AS first_year, MAX(year) AS last_year
FROM profitandloss
GROUP BY company_id
ORDER BY pl_years ASC;

-- 5. Year coverage per company: balance sheet years reported (surfaces SBIN's 0-row gap
-- and HAL's late-starting coverage, both already documented in PROGRESS.md)
SELECT company_id, COUNT(DISTINCT year) AS bs_years, MIN(year) AS first_year, MAX(year) AS last_year
FROM balancesheet
GROUP BY company_id
ORDER BY bs_years ASC;

-- 6. Companies with fewer than 10 years of P&L history (AC-02 relevant)
SELECT company_id, COUNT(DISTINCT year) AS pl_years
FROM profitandloss
GROUP BY company_id
HAVING pl_years < 10
ORDER BY pl_years ASC;

-- 7. Companies present in companies table but with zero balance sheet rows
SELECT c.id, c.company_name
FROM companies c
LEFT JOIN balancesheet b ON c.id = b.company_id
WHERE b.company_id IS NULL;

-- 8. financial_ratios coverage per company (row count per company, flags short-history
-- companies like JIOFIN/LICI/ATGL behind the AC-04 shortfall)
SELECT company_id, COUNT(*) AS ratio_rows
FROM financial_ratios
GROUP BY company_id
ORDER BY ratio_rows ASC
LIMIT 15;

-- 9. Sector distribution (confirms the real 10-sector count vs. spec's stated 11)
SELECT broad_sector, COUNT(*) AS company_count
FROM sectors
GROUP BY broad_sector
ORDER BY company_count DESC;

-- 10. Peer group coverage: how many of the 92 companies belong to a defined peer group
SELECT
    (SELECT COUNT(DISTINCT company_id) FROM peer_groups) AS companies_in_a_peer_group,
    (SELECT COUNT(*) FROM companies) AS total_companies,
    ROUND(100.0 * (SELECT COUNT(DISTINCT company_id) FROM peer_groups) / (SELECT COUNT(*) FROM companies), 1) AS coverage_pct;