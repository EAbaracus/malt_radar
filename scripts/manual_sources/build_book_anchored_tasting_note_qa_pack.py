import csv
import json
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict

ROOT = Path(r"C:\Users\eltun\Documents\malt radar")
INPUT_CSV = ROOT / "data/manual_sources/books/review_csv/book_anchored_tasting_note_rescue_review.csv"

OUT_QA_PACK = ROOT / "data/manual_sources/books/review_csv/book_anchored_tasting_note_qa_pack.csv"
OUT_ACCEPT = ROOT / "data/manual_sources/books/review_csv/book_anchored_tasting_note_accept_preview.csv"
OUT_REJECT = ROOT / "data/manual_sources/books/review_csv/book_anchored_tasting_note_reject_preview.csv"

REPORT_MD = ROOT / "output/reports/12r_book_anchored_tasting_note_qa_report.md"
GATE_TXT = ROOT / "output/reports/12r_book_anchored_tasting_note_qa_gate.txt"

stats = {
    "total_candidates": 0,
    "staging_candidate_input": 0,
    "manual_review_input": 0,
    "blocked_input": 0,
    "accepted_preview": 0,
    "needs_manual_review": 0,
    "rejected_preview": 0,
    "duplicate_removed": 0
}

reject_reasons = Counter()
source_files = Counter()

def evaluate_candidate(row):
    status = row.get("import_status", "")
    conf = float(row.get("extraction_confidence", "0"))
    wid = row.get("matched_whisky_id", "")
    snippet = row.get("candidate_text_snippet", "")
    flavors = row.get("flavor_terms", "")
    nose = row.get("nose_text", "")
    palate = row.get("palate_text", "")
    finish = row.get("finish_text", "")
    anchor = row.get("anchor_text", "")

    if status == "blocked":
        return "reject_preview", "bad_match"
        
    has_flavor_signal = bool(flavors.strip() or nose.strip() or palate.strip() or finish.strip())

    if conf >= 0.70 and wid and snippet and has_flavor_signal:
        if len(anchor) < 4:
            return "reject_preview", "generic_anchor"
        if len(snippet) > 280:
            return "reject_preview", "copyrighted_long_text_risk"
        return "accept_preview", ""
        
    if status == "manual_review":
        if not has_flavor_signal:
            return "reject_preview", "no_tasting_signal"
        return "needs_manual_review", "weak_context"
        
    return "reject_preview", "weak_context"

candidates = []
seen = set()
whisky_groups = defaultdict(list)
fieldnames = []

if INPUT_CSV.exists():
    with INPUT_CSV.open("r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        if "qa_decision" not in fieldnames:
            fieldnames.extend(["qa_decision", "reject_reason"])
            
        for row in reader:
            stats["total_candidates"] += 1
            status = row.get("import_status", "")
            
            if status == "staging_candidate":
                stats["staging_candidate_input"] += 1
            elif status == "manual_review":
                stats["manual_review_input"] += 1
            elif status == "blocked":
                stats["blocked_input"] += 1
                
            wid = row.get("matched_whisky_id", "")
            file_name = row.get("source_file", "")
            snippet = row.get("candidate_text_snippet", "")
            
            dedup_key = f"{wid}_{file_name}_{snippet}"
            if dedup_key in seen:
                stats["duplicate_removed"] += 1
                continue
            seen.add(dedup_key)
            
            qa_dec, rej_reason = evaluate_candidate(row)
            row["qa_decision"] = qa_dec
            row["reject_reason"] = rej_reason
            
            if qa_dec == "accept_preview":
                whisky_groups[wid].append(row)
            else:
                candidates.append(row)

for wid, rows in whisky_groups.items():
    if len(rows) > 1:
        rows.sort(key=lambda x: (float(x.get("extraction_confidence", 0)), len(x.get("flavor_terms", ""))), reverse=True)
        candidates.append(rows[0])
        for r in rows[1:]:
            r["qa_decision"] = "reject_preview"
            r["reject_reason"] = "duplicate"
            candidates.append(r)
            stats["duplicate_removed"] += 1
    else:
        candidates.append(rows[0])

accept_rows = []
reject_rows = []
pack_rows = candidates

for c in candidates:
    dec = c["qa_decision"]
    if dec == "accept_preview":
        stats["accepted_preview"] += 1
        accept_rows.append(c)
        source_files[c["source_file"]] += 1
    elif dec == "needs_manual_review":
        stats["needs_manual_review"] += 1
    else:
        stats["rejected_preview"] += 1
        reject_reasons[c["reject_reason"]] += 1
        reject_rows.append(c)

def write_csv(path, data):
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(data)

if fieldnames:
    write_csv(OUT_QA_PACK, pack_rows)
    write_csv(OUT_ACCEPT, accept_rows)
    write_csv(OUT_REJECT, reject_rows)

gate = "NO-GO"
if stats["accepted_preview"] >= 25:
    gate = "GO_FOR_STAGING_APPLY_DRY_RUN"
elif stats["accepted_preview"] > 0:
    gate = "WARN_GO_SMALL_BATCH"

prod_gate = "PRODUCTION_IMPORT_NO-GO"

top_whiskies = Counter()
for r in accept_rows:
    top_whiskies[r["matched_whisky_name"]] += 1

lines = []
lines.append("# 12R Book Anchored Tasting Note QA Report")
lines.append("")
lines.append(f"- generated_at: {datetime.now().isoformat(timespec='seconds')}")
lines.append("")
lines.append("## Stats")
lines.append(f"- total_candidates: {stats['total_candidates']}")
lines.append(f"- staging_candidate_input: {stats['staging_candidate_input']}")
lines.append(f"- manual_review_input: {stats['manual_review_input']}")
lines.append(f"- blocked_input: {stats['blocked_input']}")
lines.append(f"- accepted_preview: {stats['accepted_preview']}")
lines.append(f"- needs_manual_review: {stats['needs_manual_review']}")
lines.append(f"- rejected_preview: {stats['rejected_preview']}")
lines.append(f"- duplicate_removed: {stats['duplicate_removed']}")
lines.append("")
lines.append("## Gate Decision")
lines.append(f"- manual_review_gate: **{gate}**")
lines.append(f"- production_import_gate: **{prod_gate}**")
lines.append("")
lines.append("## Top Accepted Whiskies")
for w, c in top_whiskies.most_common(10):
    lines.append(f"- {w}: {c}")
lines.append("")
lines.append("## Source File Distribution (Accepted)")
for s, c in source_files.most_common():
    lines.append(f"- `{s}`: {c}")
lines.append("")
lines.append("## Reject Reasons")
for r, c in reject_reasons.most_common():
    lines.append(f"- {r}: {c}")
lines.append("")
lines.append("## Output Files")
lines.append(f"- `{OUT_QA_PACK}`")
lines.append(f"- `{OUT_ACCEPT}`")
lines.append(f"- `{OUT_REJECT}`")

REPORT_MD.write_text("\n".join(lines), encoding="utf-8")

GATE_TXT.write_text(
    f"{gate}\n{prod_gate}\nACCEPTED={stats['accepted_preview']}\nREVIEW={stats['needs_manual_review']}\nREJECTED={stats['rejected_preview']}\n",
    encoding="utf-8"
)
