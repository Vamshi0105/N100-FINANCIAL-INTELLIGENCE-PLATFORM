# Day 45 — Final Acceptance Report
Date: 2026-09-19

| Gate | Result | Evidence |
|---|---|---|
| AC-01 | PASS | companies count = 92 |
| AC-02 | PASS | 84/92 companies = 91.30% meet all three 10-year requirements |
| AC-03 | PASS | foreign_key_check rows = 0 |
| AC-04 | PASS | rows = 1155; columns = 44 |
| AC-05 | PASS | AXISBANK: manual=14.744, db=14.744, err=0.000pp; BANKBARODA: manual=17.477, db=17.477, err=0.000pp; CANBK: manual=18.176, db=18.176, err=0.000pp |
| AC-06 | FAIL | checked=5, max relative difference=16.141871050835153 |
| AC-07 | PASS | ROE>15, D/E<1, FCF>0 result count = 35 |
| AC-08 | MANUAL | Run localhost Streamlit test with a ticker and stopwatch; record result. |
| AC-09 | FAIL | FileNotFoundError('No screener CSV export found in output/ or project root') |
| AC-10 | MANUAL | Open 5 random PDFs from reports/tearsheets and visually verify no clipping/overlap. |
| AC-11 | FAIL | API not reachable: HTTPConnectionPool(host='127.0.0.1', port=8000): Max retries exceeded with url: /api/v1/health (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x0000024EF8DC1550>: Failed to establish a new connection: [WinError 10061] No connection could be made because the target machine actively refused it')) |
| AC-12 | FAIL | ConnectionError(MaxRetryError("HTTPConnectionPool(host='127.0.0.1', port=8000): Max retries exceeded with url: /api/v1/companies/TCS/ratios (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x0000024EF8DF16D0>: Failed to establish a new connection: [WinError 10061] No connection could be made because the target machine actively refused it'))")) |
| AC-13 | FAIL | ConnectionError(MaxRetryError("HTTPConnectionPool(host='127.0.0.1', port=8000): Max retries exceeded with url: /api/v1/screener?min_roe=15&max_de=1 (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x0000024EF8DF1F90>: Failed to establish a new connection: [WinError 10061] No connection could be made because the target machine actively refused it'))")) |
| AC-14 | PASS | distinct peer groups = 11 |
| AC-15 | PASS | rows=92, unique_companies=92, null_clusters=0, clusters=[0, 1, 2, 3, 4] |
| AC-16 | FAIL | ValueError("Required columns missing: ['company_id', 'type', 'rule_id', 'text', 'confidence_pct']") |
| AC-17 | FAIL | PDFs=91; <30KB=0; <50KB=0 |
| AC-18 | FAIL | returncode=0; passed=0; tail=........................................................................ [ 42%] ........................................................................ [ 84%] ...........................                                              [100%] 171 passed in 21.83s |
| AC-19 | PASS | columns=['rule_id', 'severity', 'table', 'company_id', 'year', 'field', 'issue', 'raw_value']; rows=1223 |
| AC-20 | FAIL | ModuleNotFoundError("No module named 'pypdf'") |

## Manual gates remaining
AC-08 requires a localhost Company Profile stopwatch test.
AC-10 requires visual inspection of five sampled tear sheet PDFs.