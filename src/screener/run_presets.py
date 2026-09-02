from src.screener.engine import run_screener
from src.screener.presets import PRESETS


def main():

    print("=" * 70)
    print("DAY 16 — PRESET SCREENER RESULTS")
    print("=" * 70)

    for preset_name, filters in PRESETS.items():

        print(f"\n{preset_name.upper().replace('_', ' ')}")
        print("-" * 70)

        result = run_screener(filters)

        company_count = result["company_id"].nunique()

        print(f"Company-year rows: {len(result)}")
        print(f"Distinct companies: {company_count}")

        if 5 <= company_count <= 50:
            print("STATUS: PASS")
        else:
            print("STATUS: REVIEW")

        if not result.empty:
            print("\nSample companies:")

            companies = (
                result["company_id"]
                .drop_duplicates()
                .head(10)
                .tolist()
            )

            for company in companies:
                print(company)


if __name__ == "__main__":
    main()