\# Day 43 — Performance \& Integration Testing



Date: 2026-09-17



\## 1. SQLite Performance Optimization



Added the following indexes to improve company/year-based financial queries:



\- `idx\_profitandloss\_company\_year`

\- `idx\_balancesheet\_company\_year`

\- `idx\_cashflow\_company\_year`

\- `idx\_financial\_ratios\_company\_year`

\- `idx\_market\_cap\_company\_year`

\- `idx\_stock\_prices\_company\_date`

\- `idx\_documents\_company\_year`

\- `idx\_analysis\_company\_id`



SQLite `EXPLAIN QUERY PLAN` confirmed that the new composite indexes are being used for company/year queries.



Example:



`financial\_ratios` uses:

`idx\_financial\_ratios\_company\_year`



\## 2. API Load Testing



Endpoint:



`GET /api/v1/screener?min\_roe=15`



Test:



\- 10 concurrent requests

\- Python threading

\- HTTP response validation



\### Initial result



\- Successful: 5/10

\- Failed: 5/10

\- Total elapsed: 10.415 seconds

\- Average successful response: 7.7112 seconds

\- Maximum successful response: 9.5864 seconds



\### Bottleneck identified



Each concurrent request was independently loading the full screener dataset from SQLite and recalculating composite quality scores using pandas.



\### Optimization



Implemented a thread-safe in-memory screener data cache.



The expensive:



`SQLite → pandas DataFrame → composite score`



operation is now performed once per database path.



Each request receives a copy of the cached DataFrame before filtering.



\### Final result



\- Successful: 10/10

\- Failed: 0/10

\- Total elapsed: 0.7790 seconds

\- Average response: 0.7552 seconds

\- Minimum response: 0.6505 seconds

\- Maximum response: 0.7767 seconds

\- All responses returned HTTP 200

\- All responses returned count=53



Status: PASS



\## 3. Company Profile Performance



Five Company Profile data loads were measured.



| Ticker | Load Time |

|---|---:|

| ABB | 0.0655s |

| ADANIENSOL | 0.0285s |

| ADANIENT | 0.0375s |

| ADANIGREEN | 0.0278s |

| ADANIPORTS | 0.0309s |



Average: 0.0380 seconds



Maximum: 0.0655 seconds



Target: less than 3 seconds per profile.



Status: PASS



\## 4. End-to-End Integration



FastAPI:



`127.0.0.1:8000`



Health endpoint returned:



`status: ok`



Database row counts were successfully returned.



Streamlit:



`127.0.0.1:8501`



Health endpoint returned:



`ok`



Port verification confirmed both services were simultaneously listening:



\- FastAPI: port 8000

\- Streamlit: port 8501



No port conflict detected.



\## 5. Performance Bottlenecks



\### Identified



The primary Day 43 bottleneck was repeated screener dataset loading and composite-score calculation during concurrent API requests.



\### Resolved



A thread-safe in-memory cache was introduced for the prepared screener dataset.



SQLite indexes were also added for company/year and company/date access patterns.



\### Remaining observations



Streamlit cache warnings observed during the standalone profile benchmark are caused by running Streamlit cached functions outside an active Streamlit runtime. They do not indicate a database failure.



\## 6. Day 43 Status



\- SQLite optimization: PASS

\- Query plan verification: PASS

\- API concurrent load test: PASS

\- Company Profile performance: PASS

\- FastAPI + Streamlit integration: PASS

\- Port conflict check: PASS

\- Performance documentation: COMPLETE

\- Final regression suite: PENDING

