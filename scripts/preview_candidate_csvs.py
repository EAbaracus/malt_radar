import csv
from pathlib import Path

files = sorted(Path("data/output").glob("*candidate*.csv"))

wanted_cols = [
    "source_system",
    "source_type",
    "product_name",
    "whisky_name",
    "normalized_product_name",
    "source_url",
    "nose",
    "palate",
    "finish",
    "top_flavors",
    "source_profile",
    "converted_flavor_profile",
    "flavour_camp",
    "similar_whiskies",
    "matched_master_whisky_id",
    "match_score",
    "match_method",
    "match_status",
    "approval_status",
    "import_recommendation",
]

for f in files:
    print()
    print("=" * 100)
    print("FILE:", f)
    print("=" * 100)

    try:
        with open(f, encoding="utf-8", errors="ignore", newline="") as fh:
            rows = list(csv.DictReader(fh))

        print("rows:", len(rows))
        print("columns:", list(rows[0].keys()) if rows else "NO ROWS")

        for idx, r in enumerate(rows[:5], start=1):
            print()
            print(f"--- SAMPLE {idx} ---")
            for col in wanted_cols:
                if col in r:
                    value = r.get(col)
                    if value and len(value) > 300:
                        value = value[:300] + "..."
                    print(f"{col}: {value}")

    except Exception as e:
        print("ERROR:", e)
