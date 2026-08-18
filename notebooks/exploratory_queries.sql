-- ============================================================
-- NIFTY 100 FINANCIAL INTELLIGENCE PLATFORM
-- SPRINT 1 - EXPLORATORY QUERIES
-- ============================================================


-- QUERY 01
-- Count companies
SELECT
    COUNT(*) AS total_companies
FROM companies;


-- QUERY 02
-- List companies and basic information
SELECT
    id AS ticker,
    company_name,
    website,
    face_value,
    book_value,
    roce_percentage,
    roe_percentage
FROM companies
ORDER BY company_name;


-- QUERY 03
-- Number of financial years available for each company
SELECT
    company_id,
    COUNT(DISTINCT year) AS financial_years
FROM profitandloss
GROUP BY company_id
ORDER BY financial_years DESC, company_id;


-- QUERY 04
-- Revenue and net profit by company
SELECT
    company_id,
    SUM(sales) AS total_sales,
    SUM(net_profit) AS total_net_profit,
    AVG(opm_percentage) AS average_opm
FROM profitandloss
GROUP BY company_id
ORDER BY total_sales DESC
LIMIT 20;


-- QUERY 05
-- Latest available P&L record for each company
SELECT
    p.company_id,
    p.year,
    p.sales,
    p.operating_profit,
    p.net_profit,
    p.eps
FROM profitandloss p
INNER JOIN (
    SELECT
        company_id,
        MAX(year) AS latest_year
    FROM profitandloss
    GROUP BY company_id
) latest
ON p.company_id = latest.company_id
AND p.year = latest.latest_year
ORDER BY p.net_profit DESC;


-- QUERY 06
-- Companies with highest average ROE
SELECT
    c.id AS ticker,
    c.company_name,
    c.roe_percentage,
    c.roce_percentage
FROM companies c
WHERE c.roe_percentage IS NOT NULL
ORDER BY c.roe_percentage DESC
LIMIT 20;


-- QUERY 07
-- Revenue and profit by sector
SELECT
    s.broad_sector,
    COUNT(DISTINCT s.company_id) AS companies,
    SUM(p.sales) AS total_sales,
    SUM(p.net_profit) AS total_profit
FROM sectors s
INNER JOIN profitandloss p
    ON s.company_id = p.company_id
GROUP BY s.broad_sector
ORDER BY total_sales DESC;


-- QUERY 08
-- Companies with negative or zero profit
SELECT
    company_id,
    year,
    sales,
    net_profit,
    eps
FROM profitandloss
WHERE net_profit <= 0
ORDER BY net_profit ASC;


-- QUERY 09
-- Stock price summary by company
SELECT
    company_id,
    MIN(close_price) AS minimum_close,
    MAX(close_price) AS maximum_close,
    AVG(close_price) AS average_close,
    COUNT(*) AS trading_days
FROM stock_prices
GROUP BY company_id
ORDER BY maximum_close DESC
LIMIT 20;


-- QUERY 10
-- Financial companies with revenue, profit, ROE and ROCE
SELECT
    c.id AS ticker,
    c.company_name,
    s.broad_sector,
    s.sub_sector,
    p.year,
    p.sales,
    p.net_profit,
    p.opm_percentage,
    c.roe_percentage,
    c.roce_percentage
FROM companies c
LEFT JOIN sectors s
    ON c.id = s.company_id
LEFT JOIN profitandloss p
    ON c.id = p.company_id
WHERE p.year = (
    SELECT MAX(p2.year)
    FROM profitandloss p2
    WHERE p2.company_id = p.company_id
)
ORDER BY p.net_profit DESC;