"""
Day 33 â€” PDF Company Tearsheet Template

Generates a two-page company financial tearsheet using ReportLab.

## Page 1

* Navy header with company name and ticker
* 6 KPI tiles
* 10-year Revenue bar chart
* 10-year Net Profit bar chart
* ROE and ROCE trend chart

## Page 2

* Balance Sheet composition stacked bar chart
* Cash Flow chart
* Pros and Cons
* Capital Allocation badge

Test companies:
TCS
HDFCBANK
RELIANCE
SUNPHARMA
TATASTEEL
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
PageBreak,
Paragraph,
SimpleDocTemplate,
Spacer,
Table,
TableStyle,
)

# ---------------------------------------------------------

# Project paths

# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DB_PATH = (
PROJECT_ROOT
/ "data"
/ "nifty100.db"
)

OUTPUT_DIR = (
PROJECT_ROOT
/ "output"
)

TEARSHEET_DIR = (
OUTPUT_DIR
/ "tearsheets"
)

PROS_CONS_PATH = (
OUTPUT_DIR
/ "pros_cons_generated.csv"
)

CASHFLOW_INTELLIGENCE_PATH = (
OUTPUT_DIR
/ "cashflow_intelligence.xlsx"
)

LOG_PATH = (
OUTPUT_DIR
/ "tearsheet.log"
)

# ---------------------------------------------------------

# Colors

# ---------------------------------------------------------

NAVY = colors.HexColor("#102A43")

BLUE = colors.HexColor("#2563EB")

LIGHT_BLUE = colors.HexColor("#E8F1FB")

LIGHT_GREY = colors.HexColor("#F3F4F6")

DARK_GREY = colors.HexColor("#374151")

GREEN = colors.HexColor("#15803D")

LIGHT_GREEN = colors.HexColor("#DCFCE7")

RED = colors.HexColor("#B91C1C")

LIGHT_RED = colors.HexColor("#FEE2E2")

WHITE = colors.white

# ---------------------------------------------------------

# Logging

# ---------------------------------------------------------

def configure_logging() -> None:
    """
    Configure tearsheet logging.
    """
    
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    
    logger = logging.getLogger()
    
    if logger.handlers:
        return
    
    logger.setLevel(
        logging.INFO
    )
    
    formatter = logging.Formatter(
        "%(levelname)s | %(message)s"
    )
    
    file_handler = logging.FileHandler(
        LOG_PATH,
        encoding="utf-8",
    )
    
    file_handler.setFormatter(
        formatter
    )
    
    stream_handler = logging.StreamHandler()
    
    stream_handler.setFormatter(
        formatter
    )
    
    logger.addHandler(
        file_handler
    )
    
    logger.addHandler(
        stream_handler
    )
    
# ---------------------------------------------------------

# Normalization helpers

# ---------------------------------------------------------

def normalize_company_id(
    value: Any,
    ) -> str | None:
    """
    Normalize company identifier.
    """
    
    if value is None:
        return None
    
    if pd.isna(value):
        return None
    
    company_id = str(
        value
    ).strip().upper()
    
    if not company_id:
        return None
    
    return company_id
    
def normalize_year(
    value: Any,
    ) -> int | None:
    """
    Convert database year values to integers.
    """
    
    if value is None:
        return None
    
    if pd.isna(value):
        return None
    
    text = str(
        value
    ).strip()
    
    if not text:
        return None
    
    try:
        return int(
            text[:4]
        )
    
    except (
        TypeError,
        ValueError,
    ):
        return None
    
def to_numeric(
    value: Any,
    ) -> float | None:
    """
    Safely convert values to float.
    """
    
    if value is None:
        return None
    
    if pd.isna(value):
        return None
    
    try:
    
        number = float(
            value
        )
    
        if pd.isna(number):
            return None
    
        return number
    
    except (
        TypeError,
        ValueError,
    ):
    
        return None
    
def format_number(
    value: Any,
    decimals: int = 2,
    ) -> str:
    """
    Format financial values safely.
    """
    
    number = to_numeric(
        value
    )
    
    if number is None:
        return "N/A"
    
    return (
        f"{number:,.{decimals}f}"
    )
    
def format_percent(
    value: Any,
    decimals: int = 1,
    ) -> str:
    """
    Format percentage values.
    """
    
    number = to_numeric(
        value
    )
    
    if number is None:
        return "N/A"
    
    return (
        f"{number:.{decimals}f}%"
    )
    
# ---------------------------------------------------------

# Data loading

# ---------------------------------------------------------

def load_database_data() -> dict[str, pd.DataFrame]:
    """
    Load all required tearsheet data.
    """
    
    logging.info(
        "Loading tearsheet data from %s",
        DB_PATH,
    )
    
    if not DB_PATH.exists():
    
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )
    
    queries = {
    
        "companies": """
            SELECT
                CAST(id AS TEXT) AS company_id,
                company_name
            FROM companies
        """,
    
        "profitandloss": """
            SELECT
                CAST(company_id AS TEXT) AS company_id,
                year,
                sales,
                net_profit,
                operating_profit
            FROM profitandloss
        """,
    
        "balancesheet": """
            SELECT
                CAST(company_id AS TEXT) AS company_id,
                year,
                equity_capital,
                reserves,
                borrowings,
                other_liabilities,
                total_liabilities
            FROM balancesheet
        """,
    
        "cashflow": """
            SELECT
                CAST(company_id AS TEXT) AS company_id,
                year,
                operating_activity,
                investing_activity,
                financing_activity,
                net_cash_flow
            FROM cashflow
        """,
    
        "financial_ratios": """
            SELECT
                CAST(company_id AS TEXT) AS company_id,
                year,
                return_on_equity_pct,
                return_on_capital_employed_pct,
                debt_to_equity,
                net_profit_margin_pct,
                operating_profit_margin_pct,
                free_cash_flow_cr,
                cfo_quality_ratio
            FROM financial_ratios
        """,
    
        "sectors": """
            SELECT
                CAST(company_id AS TEXT) AS company_id,
                broad_sector,
                sub_sector
            FROM sectors
        """,
    }
    
    data: dict[
        str,
        pd.DataFrame,
    ] = {}
    
    with sqlite3.connect(
        DB_PATH
    ) as connection:
    
        for name, query in queries.items():
    
            df = pd.read_sql_query(
                query,
                connection,
            )
    
            if (
                "company_id"
                in df.columns
            ):
    
                df[
                    "company_id"
                ] = df[
                    "company_id"
                ].apply(
                    normalize_company_id
                )
    
            if (
                "year"
                in df.columns
            ):
    
                df[
                    "year_numeric"
                ] = df[
                    "year"
                ].apply(
                    normalize_year
                )
    
            data[
                name
            ] = df
    
            logging.info(
                "%s rows loaded: %s",
                name,
                len(df),
            )
    
    return data
    
def load_output_data() -> dict[str, pd.DataFrame]:
    """
    Load generated intelligence files.
    """
    
    data: dict[
        str,
        pd.DataFrame,
    ] = {}
    
    if PROS_CONS_PATH.exists():
    
        pros_cons_df = pd.read_csv(
            PROS_CONS_PATH
        )
    
        pros_cons_df[
            "company_id"
        ] = pros_cons_df[
            "company_id"
        ].apply(
            normalize_company_id
        )
    
        data[
            "pros_cons"
        ] = pros_cons_df
    
        logging.info(
            "pros_cons rows loaded: %s",
            len(pros_cons_df),
        )
    
    else:
    
        logging.warning(
            "Pros and cons file not found: %s",
            PROS_CONS_PATH,
        )
    
        data[
            "pros_cons"
        ] = pd.DataFrame()
    
    if CASHFLOW_INTELLIGENCE_PATH.exists():
    
        intelligence_df = pd.read_excel(
            CASHFLOW_INTELLIGENCE_PATH
        )
    
        intelligence_df[
            "company_id"
        ] = intelligence_df[
            "company_id"
        ].apply(
            normalize_company_id
        )
    
        data[
            "cashflow_intelligence"
        ] = intelligence_df
    
        logging.info(
            "cashflow intelligence rows loaded: %s",
            len(intelligence_df),
        )
    
    else:
    
        logging.warning(
            "Cash flow intelligence file not found: %s",
            CASHFLOW_INTELLIGENCE_PATH,
        )
    
        data[
            "cashflow_intelligence"
        ] = pd.DataFrame()
    
    return data
    
# ---------------------------------------------------------

# Company data helpers

# ---------------------------------------------------------

def get_company_name(
    company_id: str,
    companies_df: pd.DataFrame,
    ) -> str:
    """
    Get company display name.
    """
    
    company = companies_df[
        companies_df[
            "company_id"
        ]
        == company_id
    ]
    
    if company.empty:
        return company_id
    
    value = company.iloc[0].get(
        "company_name"
    )
    
    if (
        value is None
        or pd.isna(value)
    ):
        return company_id
    
    return str(
        value
    ).strip()
    
def get_company_sector(
    company_id: str,
    sectors_df: pd.DataFrame,
    ) -> str:
    """
    Get company sector.
    """
    
    sector = sectors_df[
        sectors_df[
            "company_id"
        ]
        == company_id
    ]
    
    if sector.empty:
        return "N/A"
    
    row = sector.iloc[0]
    
    broad_sector = row.get(
        "broad_sector"
    )
    
    if (
        broad_sector is not None
        and pd.notna(
            broad_sector
        )
        and str(
            broad_sector
        ).strip()
    ):
    
        return str(
            broad_sector
        ).strip()
    
    sub_sector = row.get(
        "sub_sector"
    )
    
    if (
        sub_sector is not None
        and pd.notna(
            sub_sector
        )
        and str(
            sub_sector
        ).strip()
    ):
    
        return str(
            sub_sector
        ).strip()
    
    return "N/A"
    
def latest_row(
    df: pd.DataFrame,
    ) -> pd.Series | None:
    """
    Return latest company record.
    """
    
    if df.empty:
        return None
    
    working_df = df.copy()
    
    if (
        "year_numeric"
        in working_df.columns
    ):
    
        working_df = working_df.sort_values(
            by="year_numeric",
            ascending=False,
        )
    
    return working_df.iloc[0]
    
# ---------------------------------------------------------

# Styles

# ---------------------------------------------------------

def create_styles() -> dict[str, ParagraphStyle]:
    """
    Create reusable ReportLab paragraph styles.
    
    All text content uses Paragraph objects,
    providing word wrapping and preventing
    text overflow.
    """
    
    styles = getSampleStyleSheet()
    
    return {
    
        "header": ParagraphStyle(
            "TearsheetHeader",
            parent=styles[
                "Normal"
            ],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=WHITE,
            alignment=TA_LEFT,
            wordWrap="LTR",
        ),
    
        "header_subtitle": ParagraphStyle(
            "TearsheetHeaderSubtitle",
            parent=styles[
                "Normal"
            ],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=WHITE,
            alignment=TA_LEFT,
            wordWrap="LTR",
        ),
    
        "kpi_label": ParagraphStyle(
            "KPILabel",
            parent=styles[
                "Normal"
            ],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=DARK_GREY,
            alignment=TA_CENTER,
            wordWrap="LTR",
        ),
    
        "kpi_value": ParagraphStyle(
            "KPIValue",
            parent=styles[
                "Normal"
            ],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=17,
            textColor=NAVY,
            alignment=TA_CENTER,
            wordWrap="LTR",
        ),
    
        "section_title": ParagraphStyle(
            "SectionTitle",
            parent=styles[
                "Normal"
            ],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=NAVY,
            alignment=TA_LEFT,
            wordWrap="LTR",
        ),
    
        "body": ParagraphStyle(
            "Body",
            parent=styles[
                "Normal"
            ],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=DARK_GREY,
            alignment=TA_LEFT,
            wordWrap="LTR",
        ),
    
        "pro": ParagraphStyle(
            "Pro",
            parent=styles[
                "Normal"
            ],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=GREEN,
            alignment=TA_LEFT,
            wordWrap="LTR",
        ),
    
        "con": ParagraphStyle(
            "Con",
            parent=styles[
                "Normal"
            ],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=RED,
            alignment=TA_LEFT,
            wordWrap="LTR",
        ),
    
        "badge": ParagraphStyle(
            "Badge",
            parent=styles[
                "Normal"
            ],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            textColor=WHITE,
            alignment=TA_CENTER,
            wordWrap="LTR",
        ),
    }
    
# ---------------------------------------------------------

# Header

# ---------------------------------------------------------

def build_header(
    company_name: str,
    company_id: str,
    sector: str,
    styles: dict[str, ParagraphStyle],
    ) -> Table:
    """
    Build navy company header.
    """
    
    title = Paragraph(
        company_name,
        styles[
            "header"
        ],
    )
    
    subtitle = Paragraph(
        f"{company_id} | {sector}",
        styles[
            "header_subtitle"
        ],
    )
    
    table = Table(
        [
            [
                [
                    title,
                    Spacer(
                        1,
                        4,
                    ),
                    subtitle,
                ]
            ]
        ],
        colWidths=[
            7.0 * inch
        ],
    )
    
    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    NAVY,
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    14,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    14,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    12,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    12,
                ),
            ]
        )
    )
    
    return table
    
# ---------------------------------------------------------

# KPI tiles

# ---------------------------------------------------------

def build_kpi_tile(
    label: str,
    value: str,
    styles: dict[str, ParagraphStyle],
    ) -> list[Any]:
    """
    Build one KPI tile.
    """
    
    return [
        Paragraph(
            label,
            styles[
                "kpi_label"
            ],
        ),
        Spacer(
            1,
            5,
        ),
        Paragraph(
            value,
            styles[
                "kpi_value"
            ],
        ),
    ]
    
def build_kpi_section(
    latest_pnl: pd.Series | None,
    latest_ratios: pd.Series | None,
    latest_intelligence: pd.Series | None,
    styles: dict[str, ParagraphStyle],
    ) -> Table:
    """
    Build six KPI tiles.
    """
    
    sales = (
        latest_pnl.get(
            "sales"
        )
        if latest_pnl is not None
        else None
    )
    
    net_profit = (
        latest_pnl.get(
            "net_profit"
        )
        if latest_pnl is not None
        else None
    )
    
    roe = (
        latest_ratios.get(
            "return_on_equity_pct"
        )
        if latest_ratios is not None
        else None
    )
    
    roce = (
        latest_ratios.get(
            "return_on_capital_employed_pct"
        )
        if latest_ratios is not None
        else None
    )
    
    debt_equity = (
        latest_ratios.get(
            "debt_to_equity"
        )
        if latest_ratios is not None
        else None
    )
    
    cfo_quality = (
        latest_intelligence.get(
            "cfo_quality_score"
        )
        if latest_intelligence is not None
        else None
    )
    
    tiles = [
    
        build_kpi_tile(
            "Revenue",
            format_number(
                sales,
                0,
            ),
            styles,
        ),
    
        build_kpi_tile(
            "Net Profit",
            format_number(
                net_profit,
                0,
            ),
            styles,
        ),
    
        build_kpi_tile(
            "ROE",
            format_percent(
                roe,
            ),
            styles,
        ),
    
        build_kpi_tile(
            "ROCE",
            format_percent(
                roce,
            ),
            styles,
        ),
    
        build_kpi_tile(
            "Debt / Equity",
            format_number(
                debt_equity,
            ),
            styles,
        ),
    
        build_kpi_tile(
            "CFO Quality",
            format_number(
                cfo_quality,
            ),
            styles,
        ),
    ]
    
    data = [
        tiles[
            0:3
        ],
        tiles[
            3:6
        ],
    ]
    
    table = Table(
        data,
        colWidths=[
            2.28 * inch,
            2.28 * inch,
            2.28 * inch,
        ],
        rowHeights=[
            0.8 * inch,
            0.8 * inch,
        ],
    )
    
    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    LIGHT_GREY,
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor(
                        "#D1D5DB"
                    ),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
            ]
        )
    )
    
    return table
    
# ---------------------------------------------------------

# Placeholder chart

# ---------------------------------------------------------

def build_chart_placeholder(
    title: str,
    width: float,
    height: float,
    styles: dict[str, ParagraphStyle],
    ) -> Table:
    """
    Temporary chart placeholder.
    
    Real matplotlib charts will be added
    in the next step.
    """
    
    content = Paragraph(
        f"{title}<br/><br/>Chart will be rendered here.",
        styles[
            "body"
        ],
    )
    
    table = Table(
        [
            [
                content
            ]
        ],
        colWidths=[
            width
        ],
        rowHeights=[
            height
        ],
    )
    
    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    LIGHT_GREY,
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.8,
                    colors.HexColor(
                        "#9CA3AF"
                    ),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "ALIGN",
                    (0, 0),
                    (-1, -1),
                    "CENTER",
                ),
            ]
        )
    )
    
    return table
    
# ---------------------------------------------------------

# Page 1

# ---------------------------------------------------------

def build_page_one(
    company_id: str,
    data: dict[str, pd.DataFrame],
    output_data: dict[str, pd.DataFrame],
    styles: dict[str, ParagraphStyle],
    ) -> list[Any]:
    """
    Build Page 1 of the tearsheet.
    """
    
    companies_df = data[
        "companies"
    ]
    
    pnl_df = data[
        "profitandloss"
    ]
    
    ratios_df = data[
        "financial_ratios"
    ]
    
    sectors_df = data[
        "sectors"
    ]
    
    intelligence_df = output_data[
        "cashflow_intelligence"
    ]
    
    company_name = get_company_name(
        company_id,
        companies_df,
    )
    
    sector = get_company_sector(
        company_id,
        sectors_df,
    )
    
    company_pnl = pnl_df[
        pnl_df[
            "company_id"
        ]
        == company_id
    ].copy()
    
    company_ratios = ratios_df[
        ratios_df[
            "company_id"
        ]
        == company_id
    ].copy()
    
    company_intelligence = intelligence_df[
        intelligence_df[
            "company_id"
        ]
        == company_id
    ].copy()
    
    latest_pnl = latest_row(
        company_pnl
    )
    
    latest_ratios = latest_row(
        company_ratios
    )
    
    latest_intelligence = (
        company_intelligence.iloc[0]
        if not company_intelligence.empty
        else None
    )
    
    story: list[Any] = []
    
    story.append(
        build_header(
            company_name,
            company_id,
            sector,
            styles,
        )
    )
    
    story.append(
        Spacer(
            1,
            10,
        )
    )
    
    story.append(
        build_kpi_section(
            latest_pnl,
            latest_ratios,
            latest_intelligence,
            styles,
        )
    )
    
    story.append(
        Spacer(
            1,
            12,
        )
    )
    
    story.append(
        Paragraph(
            "10-Year Financial Performance",
            styles[
                "section_title"
            ],
        )
    )
    
    story.append(
        Spacer(
            1,
            6,
        )
    )
    
    revenue_chart = build_chart_placeholder(
        "Revenue Trend",
        3.35 * inch,
        2.2 * inch,
        styles,
    )
    
    profit_chart = build_chart_placeholder(
        "Net Profit Trend",
        3.35 * inch,
        2.2 * inch,
        styles,
    )
    
    chart_table = Table(
        [
            [
                revenue_chart,
                profit_chart,
            ]
        ],
        colWidths=[
            3.4 * inch,
            3.4 * inch,
        ],
    )
    
    chart_table.setStyle(
        TableStyle(
            [
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
            ]
        )
    )
    
    story.append(
        chart_table
    )
    
    story.append(
        Spacer(
            1,
            12,
        )
    )
    
    story.append(
        Paragraph(
            "ROE and ROCE Trend",
            styles[
                "section_title"
            ],
        )
    )
    
    story.append(
        Spacer(
            1,
            6,
        )
    )
    
    story.append(
        build_chart_placeholder(
            "ROE & ROCE Dual-Axis Trend",
            6.8 * inch,
            2.2 * inch,
            styles,
        )
    )
    
    return story
    
# ---------------------------------------------------------

# Page 2

# ---------------------------------------------------------

def build_page_two(
    company_id: str,
    data: dict[str, pd.DataFrame],
    output_data: dict[str, pd.DataFrame],
    styles: dict[str, ParagraphStyle],
    ) -> list[Any]:
    """
    Build Page 2 of the tearsheet.
    """
    
    pros_cons_df = output_data[
        "pros_cons"
    ]
    
    intelligence_df = output_data[
        "cashflow_intelligence"
    ]
    
    company_pros_cons = pros_cons_df[
        pros_cons_df[
            "company_id"
        ]
        == company_id
    ].copy()
    
    company_intelligence = intelligence_df[
        intelligence_df[
            "company_id"
        ]
        == company_id
    ].copy()
    
    story: list[Any] = []
    
    story.append(
        Paragraph(
            "Balance Sheet Composition",
            styles[
                "section_title"
            ],
        )
    )
    
    story.append(
        Spacer(
            1,
            6,
        )
    )
    
    story.append(
        build_chart_placeholder(
            "Equity / Borrowings / Other Liabilities",
            6.8 * inch,
            2.1 * inch,
            styles,
        )
    )
    
    story.append(
        Spacer(
            1,
            12,
        )
    )
    
    story.append(
        Paragraph(
            "Latest Year Cash Flow",
            styles[
                "section_title"
            ],
        )
    )
    
    story.append(
        Spacer(
            1,
            6,
        )
    )
    
    story.append(
        build_chart_placeholder(
            "CFO / CFI / CFF / Net Cash Flow",
            6.8 * inch,
            1.6 * inch,
            styles,
        )
    )
    
    story.append(
        Spacer(
            1,
            12,
        )
    )
    
    pros = company_pros_cons[
        company_pros_cons[
            "type"
        ]
        .astype(
            str
        )
        .str.lower()
        == "pro"
    ]
    
    cons = company_pros_cons[
        company_pros_cons[
            "type"
        ]
        .astype(
            str
        )
        .str.lower()
        == "con"
    ]
    
    pros_content: list[Any] = [
        Paragraph(
            "Pros",
            styles[
                "section_title"
            ],
        ),
        Spacer(
            1,
            5,
        ),
    ]
    
    if pros.empty:
    
        pros_content.append(
            Paragraph(
                "No pros available.",
                styles[
                    "body"
                ],
            )
        )
    
    else:
    
        for _, row in pros.head(
            5
        ).iterrows():
    
            text = str(
                row.get(
                    "text",
                    "",
                )
            ).strip()
    
            pros_content.append(
                Paragraph(
                    f"â€¢ {text}",
                    styles[
                        "pro"
                    ],
                )
            )
    
            pros_content.append(
                Spacer(
                    1,
                    4,
                )
            )
    
    cons_content: list[Any] = [
        Paragraph(
            "Cons",
            styles[
                "section_title"
            ],
        ),
        Spacer(
            1,
            5,
        ),
    ]
    
    if cons.empty:
    
        cons_content.append(
            Paragraph(
                "No cons available.",
                styles[
                    "body"
                ],
            )
        )
    
    else:
    
        for _, row in cons.head(
            5
        ).iterrows():
    
            text = str(
                row.get(
                    "text",
                    "",
                )
            ).strip()
    
            cons_content.append(
                Paragraph(
                    f"â€¢ {text}",
                    styles[
                        "con"
                    ],
                )
            )
    
            cons_content.append(
                Spacer(
                    1,
                    4,
                )
            )
    
    pros_cons_table = Table(
        [
            [
                pros_content,
                cons_content,
            ]
        ],
        colWidths=[
            3.4 * inch,
            3.4 * inch,
        ],
    )
    
    pros_cons_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (0, 0),
                    LIGHT_GREEN,
                ),
                (
                    "BACKGROUND",
                    (1, 0),
                    (1, 0),
                    LIGHT_RED,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor(
                        "#D1D5DB"
                    ),
                ),
                (
                    "INNERGRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor(
                        "#D1D5DB"
                    ),
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
            ]
        )
    )
    
    story.append(
        pros_cons_table
    )
    
    story.append(
        Spacer(
            1,
            12,
        )
    )
    
    capital_allocation = (
        "N/A"
    )
    
    if not company_intelligence.empty:
    
        value = company_intelligence.iloc[
            0
        ].get(
            "capital_allocation_label"
        )
    
        if (
            value is not None
            and pd.notna(
                value
            )
        ):
    
            capital_allocation = str(
                value
            ).strip()
    
    badge = Table(
        [
            [
                Paragraph(
                    capital_allocation,
                    styles[
                        "badge"
                    ],
                )
            ]
        ],
        colWidths=[
            3.2 * inch
        ],
    )
    
    badge.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    NAVY,
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.8,
                    NAVY,
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    10,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    10,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
            ]
        )
    )
    
    capital_table = Table(
        [
            [
                Paragraph(
                    "Capital Allocation",
                    styles[
                        "section_title"
                    ],
                ),
                badge,
            ]
        ],
        colWidths=[
            3.5 * inch,
            3.3 * inch,
        ],
    )
    
    capital_table.setStyle(
        TableStyle(
            [
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
            ]
        )
    )
    
    story.append(
        capital_table
    )
    
    return story
    
# ---------------------------------------------------------

# PDF generation

# ---------------------------------------------------------

def generate_tearsheet(
    company_id: str,
    data: dict[str, pd.DataFrame],
    output_data: dict[str, pd.DataFrame],
    ) -> Path:
    """
    Generate two-page PDF tearsheet.
    """
    
    company_id = normalize_company_id(
        company_id
    )
    
    if company_id is None:
    
        raise ValueError(
            "Invalid company_id"
        )
    
    TEARSHEET_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    
    output_path = (
        TEARSHEET_DIR
        / f"{company_id}_tearsheet.pdf"
    )
    
    document = SimpleDocTemplate(
        str(
            output_path
        ),
        pagesize=A4,
        rightMargin=0.5 * inch,
        leftMargin=0.5 * inch,
        topMargin=0.45 * inch,
        bottomMargin=0.45 * inch,
        title=f"{company_id} Financial Tearsheet",
        author="N100 Financial Intelligence Platform",
    )
    
    styles = create_styles()
    
    story: list[Any] = []
    
    story.extend(
        build_page_one(
            company_id,
            data,
            output_data,
            styles,
        )
    )
    
    story.append(
        PageBreak()
    )
    
    story.extend(
        build_page_two(
            company_id,
            data,
            output_data,
            styles,
        )
    )
    
    document.build(
        story
    )
    
    logging.info(
        "Tearsheet generated: %s",
        output_path,
    )
    
    return output_path
    
# ---------------------------------------------------------

# Test runner

# ---------------------------------------------------------

TEST_COMPANIES = [
"TCS",
"HDFCBANK",
"RELIANCE",
"SUNPHARMA",
"TATASTEEL",
]

def run_tearsheet_tests() -> None:
    """
    Generate test tearsheets for
    five companies from different sectors.
    """
    
    configure_logging()
    
    logging.info(
        "Starting Day 33 PDF Tearsheet Template"
    )
    
    data = load_database_data()
    
    output_data = load_output_data()
    
    generated_files = []
    
    for company_id in TEST_COMPANIES:
    
        logging.info(
            "Generating tearsheet for %s",
            company_id,
        )
    
        output_path = generate_tearsheet(
            company_id,
            data,
            output_data,
        )
    
        generated_files.append(
            output_path
        )
    
    print(
        "\nDay 33 Tearsheet Template "
        "completed successfully."
    )
    
    print(
        f"Test companies generated: "
        f"{len(generated_files)}"
    )
    
    print(
        "\nGenerated PDFs:"
    )
    
    for path in generated_files:
    
        print(
            f"  {path}"
        )
    
# ---------------------------------------------------------

# Main execution

# ---------------------------------------------------------

if __name__ == "__main__":


    run_tearsheet_tests()

