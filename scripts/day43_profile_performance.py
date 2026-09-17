import time
import statistics

import streamlit as st

from src.dashboard.utils.db import (
    get_company_profile,
    get_ratios,
    get_pl,
    get_pros_cons,
)


TICKERS = [
    "ABB",
    "ADANIENSOL",
    "ADANIENT",
    "ADANIGREEN",
    "ADANIPORTS",
]


def measure_profile(ticker):
    # Clear Streamlit's cache so every ticker represents
    # a fresh profile data load.
    st.cache_data.clear()

    start = time.perf_counter()

    profile = get_company_profile(ticker)
    ratios = get_ratios(ticker)
    pl = get_pl(ticker)
    pros_cons = get_pros_cons(ticker)

    elapsed = time.perf_counter() - start

    return {
        "ticker": ticker,
        "elapsed": elapsed,
        "profile_rows": len(profile),
        "ratio_rows": len(ratios),
        "pl_rows": len(pl),
        "pros_cons_rows": len(pros_cons),
    }


def main():
    print("=" * 70)
    print("DAY 43 - COMPANY PROFILE PERFORMANCE TEST")
    print("=" * 70)
    print("Tickers:", ", ".join(TICKERS))
    print("Target: each profile load < 3 seconds")
    print()

    results = []

    for ticker in TICKERS:
        result = measure_profile(ticker)
        results.append(result)

        print(
            f"{ticker:12s} | "
            f"{result['elapsed']:.4f}s | "
            f"profile={result['profile_rows']} | "
            f"ratios={result['ratio_rows']} | "
            f"pl={result['pl_rows']} | "
            f"pros_cons={result['pros_cons_rows']}"
        )

    timings = [r["elapsed"] for r in results]

    print()
    print("-" * 70)
    print("SUMMARY")
    print("-" * 70)

    print(f"Average profile load : {statistics.mean(timings):.4f}s")
    print(f"Minimum profile load : {min(timings):.4f}s")
    print(f"Maximum profile load : {max(timings):.4f}s")

    passed = all(t < 3.0 for t in timings)

    print()
    print("=" * 70)

    if passed:
        print("PASS - All 5 Company Profile loads completed within 3 seconds")
    else:
        print("FAIL - One or more Company Profile loads exceeded 3 seconds")

    print("=" * 70)


if __name__ == "__main__":
    main()