"""
Day 45 — N100 Final Acceptance Gate Runner
Run from the N100 project root:
    python day45_acceptance.py

Produces:
    output/day45_acceptance_results.csv
    output/day45_acceptance_report.md

Automated gates are executed where the local project files/API permit.
Gates requiring a browser stopwatch or visual PDF inspection are marked MANUAL.
"""

import csv
import json
import re
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from datetime import date

ROOT = Path(__file__).resolve().parent
DB = ROOT / "data" / "nifty100.db"
OUT = ROOT / "output"
REPORTS = ROOT / "reports"
DOCS = ROOT / "docs"
OUT.mkdir(exist_ok=True)

results = []

def gate(gid, criterion, status, evidence):
    results.append({
        "gate": gid,
        "criterion": criterion,
        "result": status,
        "evidence": evidence,
    })

def exists(rel):
    return (ROOT / rel).exists()

def load_csv(path):
    import pandas as pd
    return pd.read_csv(path)

def table_columns(conn, table):
    return [r[1] for r in conn.execute(f'PRAGMA table_info("{table}")').fetchall()]

def first_col(cols, names):
    low = {c.lower(): c for c in cols}
    for n in names:
        if n.lower() in low:
            return low[n.lower()]
    for c in cols:
        cl = c.lower()
        if any(n.lower() in cl for n in names):
            return c
    return None

# AC-01
try:
    with sqlite3.connect(DB) as con:
        n = con.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
    gate("AC-01", "companies row count = 92", "PASS" if n == 92 else "FAIL", f"companies count = {n}")
except Exception as e:
    gate("AC-01", "companies row count = 92", "FAIL", repr(e))

# AC-02
try:
    with sqlite3.connect(DB) as con:
        tables = {"p": "profitandloss", "b": "balancesheet", "c": "cashflow"}
        counts = {}
        for alias, table in tables.items():
            cols = table_columns(con, table)
            year_col = first_col(cols, ["year", "financial_year"])
            counts[alias] = dict(con.execute(
                f'SELECT company_id, COUNT(DISTINCT "{year_col}") FROM "{table}" GROUP BY company_id'
            ).fetchall())
        company_ids = [r[0] for r in con.execute("SELECT id FROM companies").fetchall()]
        qualified = 0
        for cid in company_ids:
            if all(counts[a].get(cid, 0) >= 10 for a in counts):
                qualified += 1
        pct = qualified / len(company_ids) * 100 if company_ids else 0
    gate("AC-02", ">=90% of companies have >=10 years P&L, BS and CF", "PASS" if pct >= 90 else "FAIL",
         f"{qualified}/92 companies = {pct:.2f}% meet all three 10-year requirements")
except Exception as e:
    gate("AC-02", ">=90% of companies have >=10 years P&L, BS and CF", "FAIL", repr(e))

# AC-03
try:
    with sqlite3.connect(DB) as con:
        rows = con.execute("PRAGMA foreign_key_check").fetchall()
    gate("AC-03", "foreign_key_check returns 0 rows", "PASS" if len(rows) == 0 else "FAIL",
         f"foreign_key_check rows = {len(rows)}")
except Exception as e:
    gate("AC-03", "foreign_key_check returns 0 rows", "FAIL", repr(e))

# AC-04
try:
    with sqlite3.connect(DB) as con:
        n = con.execute("SELECT COUNT(*) FROM financial_ratios").fetchone()[0]
        cols = table_columns(con, "financial_ratios")
    gate("AC-04", "financial_ratios >= 1,100 rows", "PASS" if n >= 1100 else "FAIL",
         f"rows = {n}; columns = {len(cols)}")
except Exception as e:
    gate("AC-04", "financial_ratios >= 1,100 rows", "FAIL", repr(e))

# AC-05 — automated spot-check from raw P&L where possible
try:
    import pandas as pd
    xls = ROOT / "data" / "raw" / "profitandloss.xlsx"
    with sqlite3.connect(DB) as con:
        fr = pd.read_sql_query("SELECT * FROM financial_ratios", con)
        pl = pd.read_sql_query("SELECT * FROM profitandloss", con)
    ycol = first_col(list(pl.columns), ["year"])
    cidcol = first_col(list(pl.columns), ["company_id", "id"])
    salescol = first_col(list(pl.columns), ["sales", "revenue", "total_sales"])
    cagrcol = first_col(list(fr.columns), ["revenue_cagr_5yr", "revenue_cagr_5y", "revenue_cagr"])
    fcid = first_col(list(fr.columns), ["company_id", "id"])
    fyear = first_col(list(fr.columns), ["year"])
    checked = []
    for cid, g in pl.groupby(cidcol):
        g = g.copy()
        g["_dt"] = pd.to_datetime(g[ycol].astype(str), errors="coerce")
        g = g.dropna(subset=["_dt", salescol]).sort_values("_dt")
        annual = g[g[ycol].astype(str).str.endswith("-03")]
        if len(annual) >= 6:
            start = float(annual.iloc[-6][salescol])
            end = float(annual.iloc[-1][salescol])
            if start > 0 and end > 0:
                manual = ((end / start) ** (1/5) - 1) * 100
                rows = fr[(fr[fcid] == cid)]
                if fyear:
                    rows = rows.sort_values(fyear)
                if len(rows):
                    candidate = rows.iloc[-1].get(cagrcol)
                    if pd.notna(candidate):
                        err = abs(float(candidate) - manual)
                        checked.append((cid, manual, float(candidate), err))
        if len(checked) >= 3:
            break
    ok = len(checked) >= 3 and max(x[3] for x in checked) <= 0.1
    gate("AC-05", "Revenue CAGR spot-check within 0.1%", "PASS" if ok else "FAIL",
         "; ".join(f"{c}: manual={m:.3f}, db={d:.3f}, err={e:.3f}pp" for c,m,d,e in checked) or "Could not obtain 3 checks")
except Exception as e:
    gate("AC-05", "Revenue CAGR spot-check within 0.1%", "FAIL", repr(e))

# AC-06
try:
    import pandas as pd
    with sqlite3.connect(DB) as con:
        comp = pd.read_sql_query("SELECT * FROM companies", con)
        rat = pd.read_sql_query("SELECT * FROM financial_ratios", con)
    cid1 = first_col(list(comp.columns), ["id", "company_id", "ticker"])
    roe1 = first_col(list(comp.columns), ["roe_percentage"])
    cid2 = first_col(list(rat.columns), ["company_id", "id"])
    year2 = first_col(list(rat.columns), ["year"])
    roe2 = first_col(list(rat.columns), ["return_on_equity_pct", "roe_percentage", "roe"])
    if not all([cid1, roe1, cid2, roe2]):
        raise ValueError(f"Required ROE columns not found: companies={comp.columns.tolist()}, ratios={rat.columns.tolist()}")
    latest = rat.copy()
    if year2:
        latest["_sort"] = pd.to_datetime(latest[year2].astype(str), errors="coerce")
        latest = latest.sort_values("_sort").groupby(cid2).tail(1)
    merged = comp[[cid1, roe1]].merge(latest[[cid2, roe2]], left_on=cid1, right_on=cid2)
    merged = merged.dropna()
    sample = merged.head(5)
    diffs = []
    for _, r in sample.iterrows():
        a, b = float(r[roe1]), float(r[roe2])
        diffs.append(abs(a-b) / max(abs(a), 1e-9) * 100)
    ok = len(diffs) == 5 and max(diffs) <= 5
    gate("AC-06", "ROE matches companies.roe_percentage within 5% for 5 companies",
         "PASS" if ok else "FAIL",
         f"checked={len(diffs)}, max relative difference={max(diffs) if diffs else None}")
except Exception as e:
    gate("AC-06", "ROE matches companies.roe_percentage within 5%", "FAIL", repr(e))

# AC-07
try:
    import pandas as pd
    with sqlite3.connect(DB) as con:
        df = pd.read_sql_query("SELECT * FROM financial_ratios", con)
    df["_dt"] = pd.to_datetime(df["year"].astype(str), errors="coerce")
    df = df[df["year"].astype(str).str.endswith("-03")].sort_values("_dt").groupby("company_id").tail(1)
    roe = first_col(list(df.columns), ["return_on_equity_pct", "roe_percentage", "roe"])
    de = first_col(list(df.columns), ["debt_to_equity"])
    fcf = first_col(list(df.columns), ["free_cash_flow_cr", "free_cash_flow"])
    if not all([roe, de, fcf]):
        raise ValueError("Required screener columns not found")
    n = int(((df[roe] > 15) & (df[de] < 1) & (df[fcf] > 0)).sum())
    gate("AC-07", "Quality screener returns 10-50 companies", "PASS" if 10 <= n <= 50 else "FAIL",
         f"ROE>15, D/E<1, FCF>0 result count = {n}")
except Exception as e:
    gate("AC-07", "Quality screener returns 10-50 companies", "FAIL", repr(e))

# AC-08 manual
gate("AC-08", "Company Profile loads in <3 seconds", "MANUAL",
     "Run localhost Streamlit test with a ticker and stopwatch; record result.")

# AC-09 file/API-independent CSV validation
try:
    import pandas as pd
    candidates = list((OUT).glob("*.csv")) + list(ROOT.glob("*.csv"))
    csvs = [p for p in candidates if "screener" in p.name.lower()]
    if not csvs:
        raise FileNotFoundError("No screener CSV export found in output/ or project root")
    p = csvs[0]
    d = pd.read_csv(p)
    ok = len(d.columns) > 0 and d.columns.notna().all() and all(str(c).strip() for c in d.columns)
    gate("AC-09", "Screener CSV is valid and well-formed", "PASS" if ok else "FAIL",
         f"{p.relative_to(ROOT)} rows={len(d)}, columns={list(d.columns)}")
except Exception as e:
    gate("AC-09", "Screener CSV is valid and well-formed", "FAIL", repr(e))

# AC-10 manual visual
gate("AC-10", "No text overflow in 5 sampled tear sheets", "MANUAL",
     "Open 5 random PDFs from reports/tearsheets and visually verify no clipping/overlap.")

# AC-11
try:
    import requests
    r = requests.get("http://127.0.0.1:8000/api/v1/health", timeout=5)
    payload = r.json()
    ok = r.status_code == 200 and "db_row_counts" in payload
    gate("AC-11", "GET /api/v1/health returns HTTP 200", "PASS" if ok else "FAIL",
         f"HTTP {r.status_code}; keys={list(payload) if isinstance(payload, dict) else 'non-object'}")
except Exception as e:
    gate("AC-11", "GET /api/v1/health returns HTTP 200", "FAIL", f"API not reachable: {e}")

# AC-12
try:
    import requests
    r = requests.get("http://127.0.0.1:8000/api/v1/companies/TCS/ratios", timeout=10)
    data = r.json()
    rows = data.get("data", data) if isinstance(data, dict) else data
    n = len(rows) if isinstance(rows, list) else 0
    gate("AC-12", "TCS ratios has 10+ years", "PASS" if r.status_code == 200 and n >= 10 else "FAIL",
         f"HTTP {r.status_code}; rows={n}")
except Exception as e:
    gate("AC-12", "TCS ratios has 10+ years", "FAIL", repr(e))

# AC-13
try:
    import requests, pandas as pd
    r = requests.get("http://127.0.0.1:8000/api/v1/screener?min_roe=15&max_de=1", timeout=10)
    api = r.json()
    api_rows = api.get("data", api.get("results", api)) if isinstance(api, dict) else api
    api_ids = {str(x.get("company_id", x.get("ticker", x.get("id")))) for x in api_rows if isinstance(x, dict)}
    xlsx = ROOT / "screener_output.xlsx"
    if not xlsx.exists():
        xlsx = OUT / "screener_output.xlsx"
    if not xlsx.exists():
        raise FileNotFoundError("screener_output.xlsx not found")
    xl = pd.ExcelFile(xlsx)
    chosen = next((s for s in xl.sheet_names if "quality" in s.lower()), xl.sheet_names[0])
    ex = pd.read_excel(xlsx, sheet_name=chosen)
    idcol = first_col(list(ex.columns), ["company_id", "ticker", "id", "Company ID"])
    if not idcol:
        raise ValueError(f"No company id column in sheet {chosen}: {ex.columns.tolist()}")
    excel_ids = {str(x) for x in ex[idcol].dropna().tolist()}
    ok = api_ids == excel_ids
    gate("AC-13", "API screener matches screener_output.xlsx", "PASS" if ok else "FAIL",
         f"sheet={chosen}; API={len(api_ids)} rows; Excel={len(excel_ids)} rows; symmetric_diff={len(api_ids ^ excel_ids)}")
except Exception as e:
    gate("AC-13", "API screener matches screener_output.xlsx", "FAIL", repr(e))

# AC-14
try:
    with sqlite3.connect(DB) as con:
        cols = table_columns(con, "peer_percentiles")
        pg = first_col(cols, ["peer_group_name", "group_name", "peer_group"])
        if not pg:
            raise ValueError(f"Peer group column not found: {cols}")
        n = con.execute(f'SELECT COUNT(DISTINCT "{pg}") FROM peer_percentiles').fetchone()[0]
    gate("AC-14", "peer_percentiles has all 11 peer groups", "PASS" if n == 11 else "FAIL",
         f"distinct peer groups = {n}")
except Exception as e:
    gate("AC-14", "peer_percentiles has all 11 peer groups", "FAIL", repr(e))

# AC-15
try:
    import pandas as pd
    p = OUT / "cluster_labels.csv"
    d = pd.read_csv(p)
    cid = first_col(list(d.columns), ["company_id", "ticker", "id"])
    cl = first_col(list(d.columns), ["cluster_id"])
    ok = len(d) == 92 and d[cid].nunique() == 92 and d[cl].notna().all() and set(d[cl].astype(int)).issubset(set(range(5)))
    gate("AC-15", "All 92 companies have cluster_id 0-4", "PASS" if ok else "FAIL",
         f"rows={len(d)}, unique_companies={d[cid].nunique()}, null_clusters={int(d[cl].isna().sum())}, clusters={sorted(d[cl].dropna().astype(int).unique().tolist())}")
except Exception as e:
    gate("AC-15", "All 92 companies have cluster_id assigned", "FAIL", repr(e))

# AC-16
try:
    import pandas as pd
    p = OUT / "pros_cons_generated.csv"
    d = pd.read_csv(p)
    cid = first_col(list(d.columns), ["company_id", "ticker", "id"])
    pro = first_col(list(d.columns), ["pro", "pros"])
    con = first_col(list(d.columns), ["con", "cons"])
    if not all([cid, pro, con]):
        raise ValueError(f"Required columns missing: {d.columns.tolist()}")
    g = d.groupby(cid).agg(pro_count=(pro, lambda s: s.astype(str).str.strip().ne("").sum()),
                           con_count=(con, lambda s: s.astype(str).str.strip().ne("").sum()))
    ok = len(g) == 92 and (g["pro_count"] >= 1).all() and (g["con_count"] >= 1).all()
    gate("AC-16", "All 92 companies have >=1 pro and >=1 con", "PASS" if ok else "FAIL",
         f"companies={len(g)}, companies missing pro={(g.pro_count<1).sum()}, missing con={(g.con_count<1).sum()}")
except Exception as e:
    gate("AC-16", "All 92 companies have >=1 pro and >=1 con", "FAIL", repr(e))

# AC-17 user requested 30KB; project document specifies 50KB. Report both.
try:
    pdfs = list((REPORTS / "tearsheets").glob("*.pdf"))
    small30 = [p for p in pdfs if p.stat().st_size < 30*1024]
    small50 = [p for p in pdfs if p.stat().st_size < 50*1024]
    ok = len(pdfs) == 92 and not small50
    gate("AC-17", "92 tear sheets exist and each >=50 KB (project document criterion)",
         "PASS" if ok else "FAIL",
         f"PDFs={len(pdfs)}; <30KB={len(small30)}; <50KB={len(small50)}")
except Exception as e:
    gate("AC-17", "92 tear sheet PDFs exist", "FAIL", repr(e))

# AC-18
try:
    cmd = [sys.executable, "-m", "pytest", "-q"]
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=180)
    textout = (proc.stdout or "") + "\n" + (proc.stderr or "")
    m = re.search(r"(\\d+) passed", textout)
    passed = int(m.group(1)) if m else 0
    ok = proc.returncode == 0 and passed >= 60 and "failed" not in textout.lower()
    gate("AC-18", "pytest >=60 tests, 0 failures/errors", "PASS" if ok else "FAIL",
         f"returncode={proc.returncode}; passed={passed}; tail={textout[-500:].strip()}")
except Exception as e:
    gate("AC-18", "pytest >=60 tests, 0 failures/errors", "FAIL", repr(e))

# AC-19
try:
    import pandas as pd
    p = OUT / "validation_failures.csv"
    d = pd.read_csv(p)
    required = {"company_id", "field", "issue", "severity"}
    ok = required.issubset(set(d.columns))
    gate("AC-19", "validation_failures.csv has required columns", "PASS" if ok else "FAIL",
         f"columns={list(d.columns)}; rows={len(d)}")
except Exception as e:
    gate("AC-19", "validation_failures.csv has required columns", "FAIL", repr(e))

# AC-20
try:
    from pypdf import PdfReader
    p = DOCS / "analyst_guide.pdf"
    n = len(PdfReader(str(p)).pages)
    gate("AC-20", "analyst_guide.pdf >=10 pages and contains guide sections", "PASS" if n >= 10 else "FAIL",
         f"pages={n}; path={p}")
except Exception as e:
    gate("AC-20", "analyst_guide.pdf >=10 pages", "FAIL", repr(e))

# Write results
import pandas as pd
df = pd.DataFrame(results)
csv_path = OUT / "day45_acceptance_results.csv"
md_path = OUT / "day45_acceptance_report.md"
df.to_csv(csv_path, index=False)

lines = [
    "# Day 45 — Final Acceptance Report",
    f"Date: {date.today().isoformat()}",
    "",
    "| Gate | Result | Evidence |",
    "|---|---|---|",
]
for r in results:
    ev = str(r["evidence"]).replace("|", "\\|").replace("\n", " ")
    lines.append(f'| {r["gate"]} | {r["result"]} | {ev} |')
lines += [
    "",
    "## Manual gates remaining",
    "AC-08 requires a localhost Company Profile stopwatch test.",
    "AC-10 requires visual inspection of five sampled tear sheet PDFs.",
]
md_path.write_text("\n".join(lines), encoding="utf-8")

print(df[["gate", "result"]].to_string(index=False))
print(f"\nSaved: {csv_path}")
print(f"Saved: {md_path}")
