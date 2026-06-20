import csv
from pathlib import Path

IN = Path("data/output/whiskeymapper_malt_radar_match_candidates.csv")
OUT_HIGH = Path("data/output/whiskeymapper_high_matches.csv")
OUT_REVIEW = Path("data/output/whiskeymapper_review_matches.csv")
OUT_NO_MATCH = Path("data/output/whiskeymapper_no_match_candidates.csv")
REPORT = Path("output/reports/189_whiskeymapper_match_qa_report.md")

if not IN.exists():
    raise FileNotFoundError(f"Missing input: {IN}")

rows = list(csv.DictReader(IN.open("r", encoding="utf-8-sig", newline="")))

high = [r for r in rows if r.get("decision") == "HIGH"]
review = [r for r in rows if r.get("decision") == "REVIEW"]
no_match = [r for r in rows if r.get("decision") == "NO_MATCH"]

def write_csv(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not data:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(data[0].keys()))
        writer.writeheader()
        writer.writerows(data)

def as_float(row, key):
    try:
        return float(row.get(key) or 0)
    except Exception:
        return 0.0

write_csv(OUT_HIGH, high)
write_csv(OUT_REVIEW, review)
write_csv(OUT_NO_MATCH, no_match)

lowest_high = sorted(high, key=lambda r: (as_float(r, "match_score"), as_float(r, "score_margin")))[:25]
top_review = sorted(review, key=lambda r: as_float(r, "match_score"), reverse=True)[:25]
top_no_match = sorted(no_match, key=lambda r: as_float(r, "match_score"), reverse=True)[:25]

REPORT.parent.mkdir(parents=True, exist_ok=True)

lines = []
lines.append("# Whiskey Mapper Match QA Report")
lines.append("")
lines.append("## Safety")
lines.append("- Production DB write: NO")
lines.append("- Match outputs only: YES")
lines.append("")
lines.append("## Counts")
lines.append(f"- Total rows: {len(rows)}")
lines.append(f"- HIGH: {len(high)}")
lines.append(f"- REVIEW: {len(review)}")
lines.append(f"- NO_MATCH: {len(no_match)}")
lines.append("")
lines.append("## Outputs")
lines.append(f"- HIGH matches: `{OUT_HIGH}`")
lines.append(f"- REVIEW matches: `{OUT_REVIEW}`")
lines.append(f"- NO_MATCH candidates: `{OUT_NO_MATCH}`")
lines.append("")
lines.append("## Lowest HIGH matches to manually spot-check")
for r in lowest_high:
    lines.append(f"- `{r.get('wm_name')}` -> `{r.get('matched_name')}` score={r.get('match_score')} margin={r.get('score_margin')} reason={r.get('reason')}")
lines.append("")
lines.append("## REVIEW queue examples")
for r in top_review:
    lines.append(f"- `{r.get('wm_name')}` -> `{r.get('matched_name')}` score={r.get('match_score')} margin={r.get('score_margin')} reason={r.get('reason')}")
lines.append("")
lines.append("## NO_MATCH examples")
for r in top_no_match:
    lines.append(f"- `{r.get('wm_name')}` -> `{r.get('matched_name')}` score={r.get('match_score')} margin={r.get('score_margin')} reason={r.get('reason')}")

REPORT.write_text("\n".join(lines), encoding="utf-8")

print(REPORT)
print("HIGH:", len(high))
print("REVIEW:", len(review))
print("NO_MATCH:", len(no_match))
