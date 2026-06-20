import json
from pathlib import Path

IN = Path("data/raw/whiskeymapper/whiskey_specific_aberlour_10.json")
REPORT = Path("output/reports/187_whiskeymapper_specific_schema_report.md")

data = json.loads(IN.read_text(encoding="utf-8"))

descriptive = data.get("descriptive", [])
flavors = data.get("flavors", [])
similars = data.get("similars", [])
stats = data.get("stats", [])

half = len(descriptive) // 2
descriptive_terms = descriptive[:half]
descriptive_weights = descriptive[half:]

similar_pairs = []
for i in range(0, len(similars), 2):
    if i + 1 < len(similars):
        similar_pairs.append((similars[i], similars[i + 1]))

lines = []
lines.append("# Whiskey Mapper Specific Endpoint Schema Report")
lines.append("")
lines.append("## Safety")
lines.append("- Production DB write: NO")
lines.append("- Raw inspection only: YES")
lines.append("")
lines.append("## Endpoint")
lines.append("- `POST https://whiskeymapper.com/api/whiskey_specific`")
lines.append("- Body example: `{\"whiskey\":\"Aberlour 10\"}`")
lines.append("")
lines.append("## Top-level keys")
for k in data.keys():
    lines.append(f"- `{k}`: `{type(data[k]).__name__}`")
lines.append("")
lines.append("## Descriptive")
lines.append(f"- Raw length: {len(descriptive)}")
lines.append(f"- Term count: {len(descriptive_terms)}")
lines.append(f"- Weight count: {len(descriptive_weights)}")
lines.append("")
lines.append("### Term weights")
for term, weight in zip(descriptive_terms, descriptive_weights):
    lines.append(f"- `{term}`: {weight}")
lines.append("")
lines.append("## Flavors")
lines.append(f"- Vector length: {len(flavors)}")
lines.append(f"- Values: `{flavors}`")
lines.append("")
lines.append("## Similars")
lines.append(f"- Raw length: {len(similars)}")
lines.append(f"- Pair count: {len(similar_pairs)}")
lines.append("")
for score, name in similar_pairs:
    lines.append(f"- `{name}`: {score}")
lines.append("")
lines.append("## Stats")
lines.append(f"- Raw length: {len(stats)}")
lines.append(f"- Values: `{stats}`")
lines.append("")
lines.append("## Interpretation")
lines.append("- `descriptive` can be used as weighted tasting tags.")
lines.append("- `flavors` can be stored as a source vector candidate, but axis meanings are unknown.")
lines.append("- `similars` can be used for recommendation validation/dry-run only.")
lines.append("- `stats` can be joined with `whiskey_table`.")

REPORT.write_text("\n".join(lines), encoding="utf-8")
print(REPORT)
