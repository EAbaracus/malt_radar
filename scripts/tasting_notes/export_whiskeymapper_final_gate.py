import csv
from pathlib import Path

MATCHES = Path("data/output/whiskeymapper_malt_radar_match_candidates.csv")
RESCUE = Path("data/output/whiskeymapper_no_match_rescue_candidates.csv")

OUT_IMPORT = Path("data/output/whiskeymapper_final_import_candidates_high_only.csv")
OUT_QA = Path("data/output/whiskeymapper_final_manual_qa_queue.csv")
OUT_GAP = Path("data/output/whiskeymapper_final_gap_candidates.csv")
REPORT = Path("output/reports/191_whiskeymapper_final_candidate_export_gate.md")

def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = []
    for row in rows:
        for k in row.keys():
            if k not in fields:
                fields.append(k)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

matches = read_csv(MATCHES)
rescue = read_csv(RESCUE)

high = [r for r in matches if r.get("decision") == "HIGH"]
review = [r for r in matches if r.get("decision") == "REVIEW"]
plain_no_match = [r for r in matches if r.get("decision") == "NO_MATCH"]

rescue_review = [r for r in rescue if r.get("rescue_decision") == "RESCUE_REVIEW"]
keep_no_match = [r for r in rescue if r.get("rescue_decision") == "KEEP_NO_MATCH"]

import_candidates = []
for r in high:
    r2 = dict(r)
    r2["final_gate"] = "IMPORT_CANDIDATE_HIGH_ONLY"
    r2["final_gate_note"] = "High confidence dry-match candidate; no DB write performed."
    import_candidates.append(r2)

qa_queue = []

for r in review:
    r2 = dict(r)
    r2["final_gate"] = "MANUAL_QA_REVIEW"
    r2["final_gate_note"] = "Original REVIEW decision from matcher."
    qa_queue.append(r2)

for r in rescue_review:
    r2 = dict(r)
    r2["final_gate"] = "MANUAL_QA_RESCUE_REVIEW"
    r2["final_gate_note"] = "Rescued from NO_MATCH; manual approval required."
    qa_queue.append(r2)

gap_candidates = []
for r in keep_no_match:
    r2 = dict(r)
    r2["final_gate"] = "KEEP_NO_MATCH_GAP"
    r2["final_gate_note"] = "No safe match; treat as source/master gap or rejected match."
    gap_candidates.append(r2)

write_csv(OUT_IMPORT, import_candidates)
write_csv(OUT_QA, qa_queue)
write_csv(OUT_GAP, gap_candidates)

lines = []
lines.append("# Whiskey Mapper Final Candidate Export Gate")
lines.append("")
lines.append("## Safety")
lines.append("- Production DB write: NO")
lines.append("- Malt Radar master CSV modified: NO")
lines.append("- Whiskey Mapper raw data modified: NO")
lines.append("- Outputs are candidate/QA/gap exports only.")
lines.append("")
lines.append("## Inputs")
lines.append(f"- Match candidates: `{MATCHES}`")
lines.append(f"- Rescue candidates: `{RESCUE}`")
lines.append("")
lines.append("## Source Counts")
lines.append(f"- Total match rows: {len(matches)}")
lines.append(f"- HIGH: {len(high)}")
lines.append(f"- REVIEW: {len(review)}")
lines.append(f"- NO_MATCH: {len(plain_no_match)}")
lines.append(f"- RESCUE_REVIEW: {len(rescue_review)}")
lines.append(f"- KEEP_NO_MATCH: {len(keep_no_match)}")
lines.append("")
lines.append("## Final Gate Outputs")
lines.append(f"- Import candidates HIGH only: {len(import_candidates)} → `{OUT_IMPORT}`")
lines.append(f"- Manual QA queue REVIEW + RESCUE_REVIEW: {len(qa_queue)} → `{OUT_QA}`")
lines.append(f"- Gap / keep no match candidates: {len(gap_candidates)} → `{OUT_GAP}`")
lines.append("")
lines.append("## Gate Decision")
lines.append("- HIGH rows may be considered for future import after final spot-check.")
lines.append("- REVIEW and RESCUE_REVIEW rows require manual approval.")
lines.append("- KEEP_NO_MATCH rows must not be imported.")
lines.append("- Production DB write remains blocked.")
lines.append("")
lines.append("## Manual QA Risk Notes")
lines.append("- Same-brand but different age/edition rows remain risky.")
lines.append("- Cross-brand rows are blocked by rescue guard.")
lines.append("- Encoding artifacts such as `â€™` should be cleaned before final human review display.")
lines.append("")

REPORT.parent.mkdir(parents=True, exist_ok=True)
REPORT.write_text("\n".join(lines), encoding="utf-8")

print(REPORT)
print("IMPORT_CANDIDATES:", len(import_candidates))
print("MANUAL_QA_QUEUE:", len(qa_queue))
print("GAP_CANDIDATES:", len(gap_candidates))
