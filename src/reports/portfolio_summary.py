"""
Day 35 â€” Portfolio Summary PDF

Generates a portfolio summary PDF with one page per company,
sorted alphabetically by ticker.

Each page contains:

* Company name
* Ticker
* Sector
* Top 6 KPIs
* Trend arrows based on the latest two available years

Trend logic:
â†‘ = improved
â†“ = declined
â†’ = flat within Â±2%
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

DB_PATH = PROJECT_ROOT / "data" / "nifty100.db"

OUTPUT_DIR = PROJECT_ROOT / "output"

REPORTS_DIR = PROJECT_ROOT / "reports"

PORTFOLIO_DIR = REPORTS_DIR / "portfolio"

PORTFOLIO_OUTPUT_PATH = (
PORTFOLIO_DIR
/ "portfolio_summary.pdf"
)

CASHFLOW_INTELLIGENCE_PATH = (
OUTPUT_DIR
/ "cashflow_intelligence.xlsx"
)

LOG_PATH = (
OUTPUT_DIR
/ "portfolio_summary.log"
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

RED = colors.HexColor("#B91C1C")

GREY = colors.HexColor("#6B7280")

WHITE = colors.white

# ---------------------------------------------------------

# Logging

# ---------------------------------------------------------

def configure_logging() -> None:
    """
    Configure portfolio summary logging.
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
    Convert year values to integer.
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
    Format numeric value.
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
    Format percentage value.
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
    Load required data from SQLite database.
    """
    
    logging.info(
        "Loading portfolio summary data from %s",
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
                net_profit
            FROM profitandloss
        """,
    
        "financial_ratios": """
            SELECT
                CAST(company_id AS TEXT) AS company_id,
                year,
                return_on_equity_pct,
                return_on_capital_employed_pct,
                debt_to_equity
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
    
def load_cashflow_intelligence() -> pd.DataFrame:
    """
    Load cash flow intelligence output.
    """
    
    if not CASHFLOW_INTELLIGENCE_PATH.exists():
    
        logging.warning(
            "Cash flow intelligence file not found: %s",
            CASHFLOW_INTELLIGENCE_PATH,
        )
    
        return pd.DataFrame()
    
    df = pd.read_excel(
        CASHFLOW_INTELLIGENCE_PATH
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
    
    logging.info(
        "cashflow intelligence rows loaded: %s",
        len(df),
    )
    
    return df
    
# ---------------------------------------------------------

# Company helpers

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
    
    value = company.iloc[
        0
    ].get(
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
    
    row = sector.iloc[
        0
    ]
    
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
    
def get_latest_two_rows(
    df: pd.DataFrame,
    ) -> tuple[
    pd.Series | None,
    pd.Series | None,
    ]:
    """
    Return latest and previous rows.
    """
    
    if df.empty:
        return None, None
    
    working_df = df.copy()
    
    if (
        "year_numeric"
        in working_df.columns
    ):
    
        working_df = working_df.sort_values(
            by="year_numeric",
            ascending=False,
        )
    
    latest = working_df.iloc[
        0
    ]
    
    previous = None
    
    if len(
        working_df
    ) >= 2:
    
        previous = working_df.iloc[
            1
        ]
    
    return latest, previous
    
# ---------------------------------------------------------

# Trend logic

# ---------------------------------------------------------

def get_trend_arrow(
    latest_value: Any,
    previous_value: Any,
    inverse: bool = False,
    ) -> tuple[str, Any]:
    """
    Return trend arrow and arrow color.
    
    â†‘ = improved
    â†“ = declined
    â†’ = flat within Â±2%
    
    inverse=True is used for metrics
    where lower values are better,
    such as Debt / Equity.
    """
    
    latest = to_numeric(
        latest_value
    )
    
    previous = to_numeric(
        previous_value
    )
    
    if (
        latest is None
        or previous is None
    ):
    
        return "â†’", GREY
    
    if previous == 0:
    
        if latest == 0:
            return "â†’", GREY
    
        if inverse:
    
            if latest < previous:
                return "â†‘", GREEN
    
            return "â†“", RED
    
        return "â†‘", GREEN
    
    change_pct = (
        (latest - previous)
        / abs(previous)
        * 100
    )
    
    if abs(
        change_pct
    ) <= 2:
    
        return "â†’", GREY
    
    if inverse:
    
        if change_pct < 0:
            return "â†‘", GREEN
    
        return "â†“", RED
    
    if change_pct > 0:
        return "â†‘", GREEN
    
    return "â†“", RED
    
# ---------------------------------------------------------

# Styles

# ---------------------------------------------------------

def create_styles() -> dict[str, ParagraphStyle]:
    """
    Create reusable ReportLab styles.
    """
    
    styles = getSampleStyleSheet()
    
    return {
    
        "header": ParagraphStyle(
            "PortfolioHeader",
            parent=styles[
                "Normal"
            ],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=24,
            textColor=WHITE,
            alignment=TA_LEFT,
            wordWrap="LTR",
        ),
    
        "subtitle": ParagraphStyle(
            "PortfolioSubtitle",
            parent=styles[
                "Normal"
            ],
            fontName="Helvetica",
            fontSize=10,
            leading=13,
            textColor=WHITE,
            alignment=TA_LEFT,
            wordWrap="LTR",
        ),
    
        "section_title": ParagraphStyle(
            "PortfolioSectionTitle",
            parent=styles[
                "Normal"
            ],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            textColor=NAVY,
            alignment=TA_LEFT,
            wordWrap="LTR",
        ),
    
        "kpi_label": ParagraphStyle(
            "PortfolioKPILabel",
            parent=styles[
                "Normal"
            ],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=DARK_GREY,
            alignment=TA_LEFT,
            wordWrap="LTR",
        ),
    
        "kpi_value": ParagraphStyle(
            "PortfolioKPIValue",
            parent=styles[
                "Normal"
            ],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=17,
            textColor=NAVY,
            alignment=TA_LEFT,
            wordWrap="LTR",
        ),
    
        "arrow": ParagraphStyle(
            "PortfolioArrow",
            parent=styles[
                "Normal"
            ],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=18,
            alignment=TA_CENTER,
            wordWrap="LTR",
        ),
    
        "footer": ParagraphStyle(
            "PortfolioFooter",
            parent=styles[
                "Normal"
            ],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=GREY,
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
    Build company page header.
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
            "subtitle"
        ],
    )
    
    table = Table(
        [
            [
                [
                    title,
                    Spacer(
                        1,
                        5,
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
                    16,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    16,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    14,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    14,
                ),
            ]
        )
    )
    
    return table
    
# ---------------------------------------------------------

# KPI row

# ---------------------------------------------------------

def build_kpi_row(
    label: str,
    value: str,
    arrow: str,
    arrow_color: Any,
    styles: dict[str, ParagraphStyle],
    ) -> list[Any]:
    """
    Build one KPI table row.
    """
    
    arrow_style = ParagraphStyle(
        f"Arrow_{label}",
        parent=styles[
            "arrow"
        ],
        textColor=arrow_color,
    )
    
    return [
    
        Paragraph(
            label,
            styles[
                "kpi_label"
            ],
        ),
    
        Paragraph(
            value,
            styles[
                "kpi_value"
            ],
        ),
    
        Paragraph(
            arrow,
            arrow_style,
        ),
    ]
    
def build_kpi_table(
    company_id: str,
    pnl_df: pd.DataFrame,
    ratios_df: pd.DataFrame,
    intelligence_df: pd.DataFrame,
    styles: dict[str, ParagraphStyle],
    ) -> Table:
    """
    Build top 6 KPI table with trend arrows.
    """
    
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
    
    latest_pnl, previous_pnl = get_latest_two_rows(
        company_pnl
    )
    
    latest_ratios, previous_ratios = (
        get_latest_two_rows(
            company_ratios
        )
    )
    
    latest_intelligence = None
    
    if not company_intelligence.empty:
    
        latest_intelligence = (
            company_intelligence.iloc[
                0
            ]
        )
    
    kpis = []
    
    # Revenue
    
    latest_revenue = (
        latest_pnl.get(
            "sales"
        )
        if latest_pnl is not None
        else None
    )
    
    previous_revenue = (
        previous_pnl.get(
            "sales"
        )
        if previous_pnl is not None
        else None
    )
    
    arrow, arrow_color = get_trend_arrow(
        latest_revenue,
        previous_revenue,
    )
    
    kpis.append(
        build_kpi_row(
            "Revenue",
            format_number(
                latest_revenue,
                0,
            ),
            arrow,
            arrow_color,
            styles,
        )
    )
    
    # Net Profit
    
    latest_profit = (
        latest_pnl.get(
            "net_profit"
        )
        if latest_pnl is not None
        else None
    )
    
    previous_profit = (
        previous_pnl.get(
            "net_profit"
        )
        if previous_pnl is not None
        else None
    )
    
    arrow, arrow_color = get_trend_arrow(
        latest_profit,
        previous_profit,
    )
    
    kpis.append(
        build_kpi_row(
            "Net Profit",
            format_number(
                latest_profit,
                0,
            ),
            arrow,
            arrow_color,
            styles,
        )
    )
    
    # ROE
    
    latest_roe = (
        latest_ratios.get(
            "return_on_equity_pct"
        )
        if latest_ratios is not None
        else None
    )
    
    previous_roe = (
        previous_ratios.get(
            "return_on_equity_pct"
        )
        if previous_ratios is not None
        else None
    )
    
    arrow, arrow_color = get_trend_arrow(
        latest_roe,
        previous_roe,
    )
    
    kpis.append(
        build_kpi_row(
            "ROE",
            format_percent(
                latest_roe,
            ),
            arrow,
            arrow_color,
            styles,
        )
    )
    
    # ROCE
    
    latest_roce = (
        latest_ratios.get(
            "return_on_capital_employed_pct"
        )
        if latest_ratios is not None
        else None
    )
    
    previous_roce = (
        previous_ratios.get(
            "return_on_capital_employed_pct"
        )
        if previous_ratios is not None
        else None
    )
    
    arrow, arrow_color = get_trend_arrow(
        latest_roce,
        previous_roce,
    )
    
    kpis.append(
        build_kpi_row(
            "ROCE",
            format_percent(
                latest_roce,
            ),
            arrow,
            arrow_color,
            styles,
        )
    )
    
    # Debt / Equity
    
    latest_de = (
        latest_ratios.get(
            "debt_to_equity"
        )
        if latest_ratios is not None
        else None
    )
    
    previous_de = (
        previous_ratios.get(
            "debt_to_equity"
        )
        if previous_ratios is not None
        else None
    )
    
    arrow, arrow_color = get_trend_arrow(
        latest_de,
        previous_de,
        inverse=True,
    )
    
    kpis.append(
        build_kpi_row(
            "Debt / Equity",
            format_number(
                latest_de,
            ),
            arrow,
            arrow_color,
            styles,
        )
    )
    
    # CFO Quality
    
    cfo_quality = (
        latest_intelligence.get(
            "cfo_quality_score"
        )
        if latest_intelligence is not None
        else None
    )
    
    kpis.append(
        build_kpi_row(
            "CFO Quality",
            format_number(
                cfo_quality,
            ),
            "â†’",
            GREY,
            styles,
        )
    )
    
    table = Table(
        kpis,
        colWidths=[
            2.6 * inch,
            2.8 * inch,
            1.2 * inch,
        ],
        rowHeights=[
            0.65 * inch,
        ] * 6,
    )
    
    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    WHITE,
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.6,
                    colors.HexColor(
                        "#D1D5DB"
                    ),
                ),
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    LIGHT_BLUE,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "ALIGN",
                    (1, 0),
                    (1, -1),
                    "RIGHT",
                ),
                (
                    "ALIGN",
                    (2, 0),
                    (2, -1),
                    "CENTER",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    12,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    12,
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
    
    return table
    
# ---------------------------------------------------------

# Company page

# ---------------------------------------------------------

def build_company_page(
    company_id: str,
    data: dict[str, pd.DataFrame],
    intelligence_df: pd.DataFrame,
    styles: dict[str, ParagraphStyle],
    ) -> list[Any]:
    """
    Build one company portfolio summary page.
    """
    
    company_name = get_company_name(
        company_id,
        data[
            "companies"
        ],
    )
    
    sector = get_company_sector(
        company_id,
        data[
            "sectors"
        ],
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
            0.35 * inch,
        )
    )
    
    story.append(
        Paragraph(
            "Portfolio KPI Summary",
            styles[
                "section_title"
            ],
        )
    )
    
    story.append(
        Spacer(
            1,
            0.15 * inch,
        )
    )
    
    story.append(
        build_kpi_table(
            company_id,
            data[
                "profitandloss"
            ],
            data[
                "financial_ratios"
            ],
            intelligence_df,
            styles,
        )
    )
    
    story.append(
        Spacer(
            1,
            0.4 * inch,
        )
    )
    
    story.append(
        Paragraph(
            (
                "Trend arrows compare the latest "
                "available year with the previous year. "
                "A movement within Â±2% is considered flat."
            ),
            styles[
                "footer"
            ],
        )
    )
    
    return story
    
# ---------------------------------------------------------

# PDF generation

# ---------------------------------------------------------

def generate_portfolio_summary() -> Path:
    """
    Generate portfolio summary PDF.
    """
    
    configure_logging()
    
    logging.info(
        "Starting Day 35 Portfolio Summary PDF generation"
    )
    
    PORTFOLIO_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    
    data = load_database_data()
    
    intelligence_df = (
        load_cashflow_intelligence()
    )
    
    company_ids = sorted(
        data[
            "companies"
        ][
            "company_id"
        ]
        .dropna()
        .unique()
        .tolist()
    )
    
    logging.info(
        "Companies to include: %s",
        len(
            company_ids
        ),
    )
    
    document = SimpleDocTemplate(
        str(
            PORTFOLIO_OUTPUT_PATH
        ),
        pagesize=A4,
        rightMargin=0.5 * inch,
        leftMargin=0.5 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
        title="N100 Portfolio Summary",
        author="N100 Financial Intelligence Platform",
    )
    
    styles = create_styles()
    
    story: list[Any] = []
    
    for index, company_id in enumerate(
        company_ids
    ):
    
        logging.info(
            "Adding portfolio page for %s",
            company_id,
        )
    
        story.extend(
            build_company_page(
                company_id,
                data,
                intelligence_df,
                styles,
            )
        )
    
        if index < len(
            company_ids
        ) - 1:
    
            story.append(
                PageBreak()
            )
    
    document.build(
        story
    )
    
    logging.info(
        "Portfolio summary generated: %s",
        PORTFOLIO_OUTPUT_PATH,
    )
    
    print(
        "\nDay 35 Portfolio Summary "
        "completed successfully."
    )
    
    print(
        f"Companies included: "
        f"{len(company_ids)}"
    )
    
    print(
        "\nPortfolio PDF:"
    )
    
    print(
        f"  {PORTFOLIO_OUTPUT_PATH}"
    )
    
    return PORTFOLIO_OUTPUT_PATH
    
# ---------------------------------------------------------

# Main execution

# ---------------------------------------------------------

if __name__ == "__main__":

    generate_portfolio_summary()
