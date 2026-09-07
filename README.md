N100 Financial Intelligence Platform

Project Overview



The N100 Financial Intelligence Platform is a Python-based financial analytics and investment research platform built for analysing companies in the Nifty 100 universe.



The platform collects, processes and analyses financial information and presents it through an interactive Streamlit dashboard.



The system currently supports approximately 92 companies with available financial and valuation data.



Key Features



The platform provides:



Company financial profiles

Financial ratio analysis

Revenue and profit trends

ROE and ROCE analysis

Financial screening using predefined investment presets

Peer group comparison

Peer percentile rankings

Radar chart financial profiles

Sector analysis

Capital allocation pattern analysis

Annual report access

Valuation analysis

FCF yield calculation

Sector-relative valuation flags

Technology Stack

Python

Pandas

NumPy

SQLite

Streamlit

Plotly

Matplotlib

OpenPyXL

Pytest

Project Structure

N100/

│

├── config/

│

├── data/

│   ├── nifty100.db

│   └── supporting/

│

├── db/

│

├── notebooks/

│

├── output/

│   ├── screener\_output.xlsx

│   ├── capital\_allocation.csv

│   ├── valuation\_summary.xlsx

│   └── valuation\_flags.csv

│

├── reports/

│   └── radar\_charts/

│

├── scripts/

│

├── src/

│   │

│   ├── analytics/

│   │   ├── cash\_flow.py

│   │   ├── peer.py

│   │   ├── radar.py

│   │   ├── ratios.py

│   │   └── valuation.py

│   │

│   ├── dashboard/

│   │   ├── app.py

│   │   ├── pages/

│   │   │   ├── 01\_home.py

│   │   │   ├── 02\_company\_profile.py

│   │   │   ├── 03\_screener.py

│   │   │   ├── 04\_peer\_comparison.py

│   │   │   ├── 05\_trends.py

│   │   │   ├── 06\_sectors.py

│   │   │   ├── 07\_capital.py

│   │   │   └── 08\_reports.py

│   │   │

│   │   └── utils/

│   │       └── db.py

│   │

│   └── screener/

│       └── presets.py

│

├── tests/

│

├── requirements.txt

│

└── README.md

Installation

1\. Clone or Download the Project



Open a terminal inside the project directory:



N100

2\. Create a Virtual Environment

python -m venv venv



Activate it:



venv\\Scripts\\activate

3\. Install Dependencies

pip install -r requirements.txt

Running the Dashboard



From the project root:



streamlit run src/dashboard/app.py



The Streamlit dashboard will open automatically in your browser.



Dashboard Screens



The application contains 8 interactive screens.



1\. Home



Provides an overview of the N100 Financial Intelligence Platform and navigation to the available analysis screens.



2\. Company Profile



Allows users to search for a company using:



NSE ticker

Company name



Displays:



Company information

Broad sector

Sub-sector

About company

ROE

ROCE

Net Profit Margin

Debt to Equity

Revenue CAGR

Free Cash Flow

Revenue trend

Net Profit trend

ROE trend

ROCE trend

Pros

Cons



Missing financial metrics are displayed as:



N/A



instead of causing application errors.



3\. Financial Screener



Allows users to screen companies using financial metrics and predefined investment strategies.



Available preset categories include:



Quality Compounder

Value Pick

Growth Accelerator

Dividend Champion

Debt Free Blue Chip

Turnaround Watch



Users can adjust screener criteria and download the resulting company list.



The screener download produces a valid CSV file with the required column headers.



4\. Peer Comparison



Compares companies against their assigned peer groups.



The platform calculates percentile rankings for metrics including:



ROE

ROCE

Net Profit Margin

Debt to Equity

Free Cash Flow

PAT CAGR

Revenue CAGR

EPS CAGR

Interest Coverage

Asset Turnover



Higher percentile rankings represent stronger relative performance.



For Debt to Equity:



Lower debt is considered better.



The percentile ranking is therefore inverted.



Peer Percentile Formula



Peer percentile rankings are calculated using:



(rank - 1) / (number\_of\_values - 1)



For peer groups containing only one valid company:



Percentile = 1.0



Companies without a peer group are excluded from peer percentile rankings.



Radar Charts



Financial radar charts compare each company against its peer group average.



Radar chart metrics include:



ROE

ROCE

Net Profit Margin

Debt to Equity

Free Cash Flow Score

PAT CAGR 5 Year

Revenue CAGR 5 Year

Composite Quality Score



Values are normalised between:



0.0 and 1.0



Companies without peer group assignments receive a standalone financial profile compared against the Nifty 100 average.



5\. Financial Trends



The Financial Trends screen allows users to:



Search for a company

Select multiple financial metrics

Overlay up to 3 metrics

Analyse long-term financial performance



Charts display:



Up to 10 years of available data

Historical trend lines

Data point values

Year-over-Year percentage changes



Companies with fewer than 10 years of data display the available history without causing application errors.



6\. Sector Analysis



The Sector Analysis screen provides sector-level financial analysis.



Users can select a sector and view a Plotly bubble chart.



The chart uses:



X-axis: Revenue

Y-axis: ROE

Bubble size: Market Capitalisation

Bubble grouping: Sub-sector



The screen also includes sector median KPI comparisons.



This allows users to compare companies within the same broad sector.



7\. Capital \& Cash Flow



The Capital Allocation Map classifies companies based on the signs of their cash flows.



The three cash flow components are:



CFO — Cash Flow from Operations

CFI — Cash Flow from Investing

CFF — Cash Flow from Financing



Companies are grouped into capital allocation patterns.



Examples include:



Reinvestor

Shareholder Returns

Liquidating Assets

Distress Signal

Growth Funded by Debt

Cash Accumulator

Pre-Revenue

Mixed



The screen visualises companies using an interactive treemap.



Selecting a capital allocation pattern displays the companies associated with that pattern.



Capital Allocation Patterns



The platform uses cash flow sign combinations to classify companies.



(+,-,-) = Reinvestor



(+,-,-) with high CFO/PAT = Shareholder Returns



(+,+,-) = Liquidating Assets



(-,+,+) = Distress Signal



(-,-,+) = Growth Funded by Debt



(+,+,+) = Cash Accumulator



(-,-,-) = Pre-Revenue



(+,-,+) = Mixed

8\. Annual Reports



The Annual Reports screen allows users to:



Search for a company

View available annual report years

Access BSE annual report PDF documents



Annual report links are retrieved from the documents table in SQLite.



If a report URL is unavailable or invalid, the dashboard displays:



Report unavailable



instead of crashing.



Valuation Module



The valuation module is implemented in:



src/analytics/valuation.py



It performs valuation analysis using market capitalisation and financial data.



FCF Yield



Free Cash Flow Yield is calculated as:



FCF Yield = Free Cash Flow / Market Capitalisation × 100



The platform calculates FCF yield for the available company universe.



Sector Median P/E



Companies are compared against the median P/E of their broad sector.



The latest available annual reporting period is used for sector comparisons.



Valuation Flags



Companies are classified using sector-relative P/E thresholds.



Caution

P/E > Sector Median P/E × 1.5

Discount

P/E < Sector Median P/E × 0.7

Fair

All remaining companies

Valuation Outputs



The valuation module generates:



output/valuation\_summary.xlsx



The summary contains columns including:



company\_id

company\_name

sector

P/E

P/B

EV/EBITDA

FCF\_yield\_pct

5yr\_median\_PE

PE\_vs\_sector\_median\_pct

flag



It also generates:



output/valuation\_flags.csv



This file contains companies flagged as:



Caution

Discount



along with supporting valuation data.



Data Quality and Edge Cases



During Sprint 4 testing, several data quality cases were identified.



Partial Financial History



Some companies have fewer than 10 annual financial records.



Examples include companies with:



1 year

2 years

6 years

7 years

8 years

9 years



The dashboard handles these companies by displaying the available data and showing appropriate availability messages.



Missing Financial Metrics



Financial metrics may occasionally contain:



None

NaN

Missing values



The dashboard converts missing values to:



N/A



This prevents KPI tiles and charts from crashing.



Interim Financial Records



Some companies contain interim financial periods.



For company profile calculations, the application prefers complete annual financial records where required metrics are available.



This avoids using incomplete reporting periods as the latest annual result.



Missing Peer Groups



Companies without peer group assignments are not included in peer percentile calculations.



Instead, they receive standalone comparison profiles using the broader Nifty 100 average.



Missing Annual Reports



Annual report URLs may occasionally become unavailable.



The Reports screen handles unavailable reports gracefully and displays a report availability status instead of failing.



Sprint 4 UX Decisions



Several user experience decisions were made during dashboard development.



Search Before Selection



Company screens use search and autocomplete functionality.



This improves usability when working with approximately 92 companies.



Container Width Charts



Plotly charts use:



use\_container\_width=True



This prevents charts from overflowing the dashboard width.



Missing Data Handling



Missing values are displayed as:



N/A



instead of raw Python values such as:



nan

None

Informational Messages



When data is unavailable, the dashboard displays informative messages rather than blank screens or errors.



Examples include:



Financial data is not available

Profit and Loss data is not available

No pros data available

No cons data available

Ticker not found

Performance Findings



Company Profile screen performance was tested across multiple companies.



The data loading layer uses cached database functions to reduce repeated SQLite queries.



Performance testing targeted:



Under 3 seconds per company profile load



Charts are rendered using responsive Plotly layouts to maintain usability across different browser widths.



Testing



The project uses Pytest for automated testing.



Run the complete test suite:



python -m pytest



Latest completed test result:



105 passed



The test suite covers:



Data normalisation

CAGR calculations

Profitability ratios

Financial ratios

Cash flow calculations

Leverage calculations

Screener presets

Peer group calculations

Sprint 4 Completion Status

Task	Status

Streamlit Dashboard	Complete

Home Screen	Complete

Company Profile	Complete

Financial Screener	Complete

Peer Comparison	Complete

Financial Trends	Complete

Sector Analysis	Complete

Capital Allocation Map	Complete

Annual Reports	Complete

Peer Percentile Engine	Complete

Radar Chart Engine	Complete

Capital Allocation Analysis	Complete

Valuation Module	Complete

Integration QA	Complete

Missing Data Handling	Complete

Chart Responsiveness	Complete

Automated Tests	Complete

Documentation	Complete

Sprint 4 Deliverables



Completed deliverables include:



src/dashboard/app.py

src/dashboard/pages/



with all 8 dashboard screens.



src/dashboard/utils/db.py



Cached database loader.



src/analytics/valuation.py



Valuation analysis module.



output/valuation\_summary.xlsx



Valuation summary for the company universe.



output/valuation\_flags.csv



Companies flagged as Caution or Discount.



README.md



Project documentation and dashboard instructions.



Definition of Done



Sprint 4 exit criteria:



&#x20;All 8 Streamlit screens implemented

&#x20;Dashboard handles missing financial data

&#x20;Partial data companies do not crash the application

&#x20;Charts are responsive to page width

&#x20;Screener supports CSV download

&#x20;Valuation summary generated

&#x20;Valuation flags generated

&#x20;Automated test suite passing

&#x20;105 tests passing

&#x20;README documentation completed

Run Commands

Run Dashboard

streamlit run src/dashboard/app.py

Run Tests

python -m pytest

Run Valuation Analysis

python src\\analytics\\valuation.py

Generate Capital Allocation Data

python src\\generate\_capital\_allocation.py

Project Status



N100 Financial Intelligence Platform — Sprint 4 Complete



The platform now provides an integrated financial research environment covering company analysis, screening, peer comparison, trends, sectors, capital allocation, annual reports and valuation analysis.



Step 2: Save the file



Press:



Ctrl + S



Then close Notepad.



Step 3: Verify README.md exists



Run:



dir README.md



You should now see something similar to:



README.md



Then:



type README.md



The documentation should display successfully.

