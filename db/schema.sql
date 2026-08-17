PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS peer_groups;
DROP TABLE IF EXISTS financial_ratios;
DROP TABLE IF EXISTS market_cap;
DROP TABLE IF EXISTS stock_prices;
DROP TABLE IF EXISTS sectors;
DROP TABLE IF EXISTS prosandcons;
DROP TABLE IF EXISTS documents;
DROP TABLE IF EXISTS analysis;
DROP TABLE IF EXISTS cashflow;
DROP TABLE IF EXISTS balancesheet;
DROP TABLE IF EXISTS profitandloss;
DROP TABLE IF EXISTS companies;


CREATE TABLE companies (
    id TEXT PRIMARY KEY,
    company_logo TEXT,
    company_name TEXT NOT NULL,
    chart_link TEXT,
    about_company TEXT,
    website TEXT,
    nse_profile TEXT,
    bse_profile TEXT,
    face_value REAL,
    book_value REAL,
    roce_percentage REAL,
    roe_percentage REAL
);


CREATE TABLE profitandloss (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id TEXT NOT NULL,
    year TEXT NOT NULL,
    sales REAL,
    expenses REAL,
    operating_profit REAL,
    opm_percentage REAL,
    other_income REAL,
    interest REAL,
    depreciation REAL,
    profit_before_tax REAL,
    tax_percentage REAL,
    net_profit REAL,
    eps REAL,
    dividend_payout REAL,

    UNIQUE(company_id, year),

    FOREIGN KEY(company_id)
        REFERENCES companies(id)
);


CREATE TABLE balancesheet (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id TEXT NOT NULL,
    year TEXT NOT NULL,
    equity_capital REAL,
    reserves REAL,
    borrowings REAL,
    other_liabilities REAL,
    total_liabilities REAL,
    fixed_assets REAL,
    cwip REAL,
    investments REAL,
    other_asset REAL,
    total_assets REAL,

    UNIQUE(company_id, year),

    FOREIGN KEY(company_id)
        REFERENCES companies(id)
);


CREATE TABLE cashflow (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id TEXT NOT NULL,
    year TEXT NOT NULL,
    operating_activity REAL,
    investing_activity REAL,
    financing_activity REAL,
    net_cash_flow REAL,

    UNIQUE(company_id, year),

    FOREIGN KEY(company_id)
        REFERENCES companies(id)
);


CREATE TABLE analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id TEXT NOT NULL,
    compounded_sales_growth TEXT,
    compounded_profit_growth TEXT,
    stock_price_cagr TEXT,
    roe TEXT,

    FOREIGN KEY(company_id)
        REFERENCES companies(id)
);


CREATE TABLE documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id TEXT NOT NULL,
    year INTEGER,
    annual_report TEXT,

    FOREIGN KEY(company_id)
        REFERENCES companies(id)
);


CREATE TABLE prosandcons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id TEXT NOT NULL,
    pros TEXT,
    cons TEXT,

    FOREIGN KEY(company_id)
        REFERENCES companies(id)
);


CREATE TABLE sectors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id TEXT NOT NULL,
    broad_sector TEXT,
    sub_sector TEXT,
    index_weight_pct REAL,
    market_cap_category TEXT,

    FOREIGN KEY(company_id)
        REFERENCES companies(id)
);


CREATE TABLE stock_prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id TEXT NOT NULL,
    date TEXT,
    open_price REAL,
    high_price REAL,
    low_price REAL,
    close_price REAL,
    volume REAL,
    adjusted_close REAL,

    FOREIGN KEY(company_id)
        REFERENCES companies(id)
);


CREATE TABLE market_cap (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id TEXT NOT NULL,
    year INTEGER,
    market_cap_crore REAL,
    enterprise_value_crore REAL,
    pe_ratio REAL,
    pb_ratio REAL,
    ev_ebitda REAL,
    dividend_yield_pct REAL,

    FOREIGN KEY(company_id)
        REFERENCES companies(id)
);


CREATE TABLE financial_ratios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id TEXT NOT NULL,
    year TEXT NOT NULL,
    net_profit_margin_pct REAL,
    operating_profit_margin_pct REAL,
    return_on_equity_pct REAL,
    debt_to_equity REAL,
    interest_coverage REAL,
    asset_turnover REAL,
    free_cash_flow_cr REAL,
    capex_cr REAL,
    earnings_per_share REAL,
    book_value_per_share REAL,
    dividend_payout_ratio_pct REAL,
    total_debt_cr REAL,
    cash_from_operations_cr REAL,

    FOREIGN KEY(company_id)
        REFERENCES companies(id)
);


CREATE TABLE peer_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    peer_group_name TEXT,
    company_id TEXT NOT NULL,
    is_benchmark INTEGER,

    FOREIGN KEY(company_id)
        REFERENCES companies(id)
);