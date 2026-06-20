import csv
import json
from pathlib import Path

BASE = Path("data/raw/whiskeymapper")
OUT = Path("data/output/whiskeymapper_joined_candidates.csv")
REPORT = Path("output/reports/186_whiskeymapper_joined_candidates_report.md")

table_data = json.loads((BASE / "whiskey_table.json").read_text(encoding="utf-8"))
scatter_data = json.loads((BASE / "whiskey_scatter.json").read_text(encoding="utf-8"))

table_rows = table_data["table"]

required_scatter_keys = ["Component_1", "Component_2", "Component_3", "type", "whiskey"]
missing = [k for k in required_scatter_keys if k not in scatter_data]
if missing:
    raise RuntimeError(f"Missing scatter keys: {missing}")

scatter_len = len(scatter_data["whiskey"])
if len(table_rows) != scatter_len:
    raise RuntimeError(f"Length mismatch: table={len(table_rows)} scatter={scatter_len}")

rows = []

for i, row in enumerate(table_rows):
    if len(row) < 11:
        continue

    rows.append({
        "source": "whiskeymapper",
        "row_index": i,
        "whiskey_name": row[0],
        "review_count": row[1],
        "avg_score": row[2],
        "score_dispersion": row[3],
        "category_type": row[4],
        "brand": row[5],
        "distillery": row[6],
        "owner_company": row[7],
        "latitude": row[8],
        "longitude": row[9],
        "wm_unknown_numeric": row[10],
        "scatter_whiskey": scatter_data["whiskey"][i],
        "scatter_type": scatter_data["type"][i],
        "component_1": scatter_data["Component_1"][i],
        "component_2": scatter_data["Component_2"][i],
        "component_3": scatter_data["Component_3"][i],
        "name_match_table_scatter": str(row[0] == scatter_data["whiskey"][i]).upper(),
    })

OUT.parent.mkdir(parents=True, exist_ok=True)
REPORT.parent.mkdir(parents=True, exist_ok=True)

with OUT.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)

name_mismatches = [r for r in rows if r["name_match_table_scatter"] != "TRUE"]

report = []
report.append("# Whiskey Mapper Joined Candidates Report")
report.append("")
report.append(f"- Table rows: {len(table_rows)}")
report.append(f"- Scatter rows: {scatter_len}")
report.append(f"- Joined rows: {len(rows)}")
report.append(f"- Name mismatches: {len(name_mismatches)}")
report.append("- Production DB write: NO")
report.append("")
report.append("## Output")
report.append(f"- `{OUT}`")
report.append("")
report.append("## Field interpretation")
report.append("- `component_1`, `component_2`, `component_3`: Whiskey Mapper scatter/vector coordinates")
report.append("- `avg_score`: likely community/review score")
report.append("- `score_dispersion`: likely rating spread/standard deviation")
report.append("- `review_count`: number of reviews/ratings")

if name_mismatches[:10]:
    report.append("")
    report.append("## First mismatches")
    for r in name_mismatches[:10]:
        report.append(f"- table=`{r['whiskey_name']}` scatter=`{r['scatter_whiskey']}`")

REPORT.write_text("\n".join(report), encoding="utf-8")

print(OUT)
print(REPORT)
print("joined_rows:", len(rows))
print("name_mismatches:", len(name_mismatches))
