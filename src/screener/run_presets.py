from src.screener.engine import run_screener
from src.screener.presets import PRESETS
from src.screener.export import export_screener_results


def main():

    print("=" * 70)
    print("DAY 17 — SCREENER PRESET RESULTS")
    print("=" * 70)

    preset_results = {}

    for preset_name, filters in PRESETS.items():

        print(
            f"\n{preset_name.upper().replace('_', ' ')}"
        )

        print("-" * 70)

        result = run_screener(filters)

        # Save result for Excel export
        preset_results[preset_name] = result

        company_count = (
            result["company_id"]
            .nunique()
        )

        print(
            f"Companies: {company_count}"
        )

        if not result.empty:

            print(
                "\nTop companies:"
            )

            companies = (
                result
                .sort_values(
                    "composite_quality_score",
                    ascending=False,
                )["company_id"]
                .drop_duplicates()
                .head(10)
                .tolist()
            )

            for company in companies:
                print(company)

    # -------------------------------------------------
    # EXPORT ALL PRESETS
    # -------------------------------------------------

    output_path = (
        export_screener_results(
            preset_results,
            PRESETS,
        )
    )

    print("\n" + "=" * 70)
    print(
        "EXCEL EXPORT COMPLETED"
    )
    print("=" * 70)

    print(
        f"\nFile created: {output_path}"
    )


if __name__ == "__main__":
    main()