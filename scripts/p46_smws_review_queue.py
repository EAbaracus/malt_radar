#!/usr/bin/env python
"""
P46 — SMWS Human Review Queue (staging-only, no production write)

Consumes verified P45 outputs:
  output/import/smws/staging_smws_tasting_notes.csv
  output/reports/smws_match_preview.csv
  output/reports/smws_usa_pdf_manifest.csv

Produces reviewer-facing artifacts:
  output/reports/p46_smws_review_queue.csv        (one prioritized row per staging record)
  output/reports/p46_smws_review_statistics.md
  output/reports/p46_smws_validation.md

Deterministic: pure function of inputs, sorted by priority desc then cask_no.

Priority model (transparent, reviewer-facing):
  CRITICAL : needs OCR (image-only PDF) OR empty tasting notes
  HIGH     : no confident distillery link (unlisted SMWS code)
  MEDIUM   : duplicate-cask pair in archive OR fuzzy distillery link needs review
  LOW      : fully linked + clean (review_status still pending_review)

This script NEVER writes to production.db and does NOT create a staging DB.
OCR is flagged as a required action but NOT executed (no OCR engine installed).
"""
import csv
import re
from collections import Counter
from pathlib import Path

ROOT = Path(r"C:\Users\eltun\Documents\malt radar CLEAN")
IMP = ROOT / "output/import/smws"
REP = ROOT / "output/reports"

STAGE = IMP / "staging_smws_tasting_notes.csv"
MATCH = REP / "smws_match_preview.csv"
MANIFEST = REP / "smws_usa_pdf_manifest.csv"

QUEUE = REP / "p46_smws_review_queue.csv"
STATS = REP / "p46_smws_review_statistics.md"
VALID = REP / "p46_smws_validation.md"

PRIO_RANK = {"CRITICAL": 3, "HIGH": 2, "MEDIUM": 1, "LOW": 0}
OCR_PDFS = {"005.42.pdf", "050.62.pdf", "064.60.pdf", "073.67.pdf",
            "5.42.pdf", "50.62.pdf", "64.60.pdf", "G4.6.pdf"}


def load_csv(p):
    with open(p, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    stage = load_csv(STAGE)
    match = load_csv(MATCH)
    manifest = load_csv(MANIFEST)

    match_by_file = {r["file_name"]: r for r in match}
    man_by_file = {r["file_name"]: r for r in manifest}

    # duplicate-cask pairs (cask_no appearing in >1 file)
    cask_files = {}
    for r in stage:
        c = r["cask_no"].strip()
        if c:
            cask_files.setdefault(c, []).append(r["file_name"])
    dup_casks = {c for c, fs in cask_files.items() if len(fs) > 1}

    rows = []
    for r in stage:
        fn = r["file_name"]
        cask = r["cask_no"].strip()
        m = match_by_file.get(fn, {})
        man = man_by_file.get(fn, {})
        notes = r["tasting_notes_raw"].strip()
        dist = r["distillery"].strip()
        suggestion = m.get("suggestion", "")
        needs_review = m.get("needs_review", "")

        reasons = []
        priority = "LOW"

        # CRITICAL: OCR needed or empty notes
        if fn in OCR_PDFS or man.get("pdf_type") == "scanned" or not notes:
            priority = "CRITICAL"
            reasons.append("OCR required (image-only PDF) — no text layer")
        # HIGH: no confident distillery link
        if needs_review == "yes" and suggestion.startswith("NO"):
            if priority != "CRITICAL":
                priority = "HIGH"
            reasons.append("No confident distillery link — verify SMWS cask code / distillery")
        # MEDIUM: duplicate-cask pair or fuzzy link
        if cask in dup_casks:
            if priority == "LOW":
                priority = "MEDIUM"
            others = [x for x in cask_files[cask] if x != fn]
            reasons.append(f"Duplicate cask code in archive: {', '.join(others)}")
        if suggestion.startswith("LINK") and needs_review == "yes":
            if priority == "LOW":
                priority = "MEDIUM"
            reasons.append("Fuzzy distillery link — confirm before import")

        if not reasons:
            reasons.append("Linked + clean — routine confirmation")

        rows.append({
            "priority": priority,
            "file_name": fn,
            "cask_no": cask,
            "distillery": dist,
            "region": r["region"].strip(),
            "age": r["age"].strip(),
            "abv": r["abv"].strip(),
            "extraction_confidence": r["extraction_confidence"].strip(),
            "match_suggestion": suggestion,
            "matched_distillery_name": m.get("matched_distillery_name", ""),
            "review_reason": " | ".join(reasons),
            "review_status": r["review_status"].strip(),
            "action_required": "RUN_OCR" if priority == "CRITICAL" else "VERIFY",
        })

    # deterministic sort: priority desc, then cask_no numeric, then file_name
    def cask_key(c):
        m = re.match(r"^([Gg]?)(\d+)(?:\.(\d+))?$", c)
        if not m:
            return (1e9, 0)
        return (int(m.group(2)), int(m.group(3) or 0))
    rows.sort(key=lambda x: (-PRIO_RANK[x["priority"]],) + cask_key(x["cask_no"]) + (x["file_name"],))

    cols = ["priority", "file_name", "cask_no", "distillery", "region", "age", "abv",
            "extraction_confidence", "match_suggestion", "matched_distillery_name",
            "review_reason", "review_status", "action_required"]
    with open(QUEUE, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    # statistics
    pc = Counter(r["priority"] for r in rows)
    ncask = sum(1 for r in stage if r["cask_no"].strip())
    ndist = sum(1 for r in stage if r["distillery"].strip())
    nnotes = sum(1 for r in stage if r["tasting_notes_raw"].strip())
    stats = []
    stats.append("# P46 SMWS Review — Statistics\n")
    stats.append(f"Total staging records: **{len(stage)}**\n")
    stats.append("## Priority distribution\n")
    stats.append("| Priority | Count | % |")
    stats.append("|----------|-------|---|")
    for p in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        c = pc.get(p, 0)
        stats.append(f"| {p} | {c} | {100*c/len(stage):.1f}% |")
    stats.append("\n## Field completeness (of staging)\n")
    stats.append(f"- cask_no: {ncask}/{len(stage)} ({100*ncask/len(stage):.1f}%)")
    stats.append(f"- distillery (linked): {ndist}/{len(stage)} ({100*ndist/len(stage):.1f}%)")
    stats.append(f"- tasting_notes_raw: {nnotes}/{len(stage)} ({100*nnotes/len(stage):.1f}%)")
    stats.append(f"- duplicate-cask pairs in archive: {len(dup_casks)}")
    stats.append(f"- OCR-required PDFs: {len(OCR_PDFS)}")
    stats.append("\n## Recommended review order\n")
    stats.append("1. CRITICAL — run OCR on the 8 image-only PDFs (no engine installed; out of scope to execute).")
    stats.append("2. HIGH — confirm distillery for unlisted SMWS codes against an authoritative source.")
    stats.append("3. MEDIUM — resolve duplicate-cask pairs and confirm fuzzy distillery links.")
    stats.append("4. LOW — routine confirmation of already-linked records.\n")
    with open(STATS, "w", encoding="utf-8") as f:
        f.write("\n".join(stats))

    # validation report
    val = []
    val.append("# P46 SMWS Review — Validation\n")
    checks = []
    checks.append(("queue row count == staging row count", len(rows) == len(stage), f"{len(rows)} vs {len(stage)}"))
    checks.append(("all rows have review_status=pending_review", all(r["review_status"] == "pending_review" for r in rows), ""))
    checks.append(("CRITICAL count == OCR PDF count", pc.get("CRITICAL", 0) == len(OCR_PDFS), f"{pc.get('CRITICAL',0)} vs {len(OCR_PDFS)}"))
    checks.append(("no production write performed", True, "script has no DB connection"))
    val.append("| Check | Result | Detail |")
    val.append("|-------|--------|--------|")
    allok = True
    for name, ok, detail in checks:
        val.append(f"| {name} | {'PASS' if ok else 'FAIL'} | {detail} |")
        allok = allok and ok
    val.append(f"\n**P46 validation: {'PASS' if allok else 'FAIL'}**\n")
    with open(VALID, "w", encoding="utf-8") as f:
        f.write("\n".join(val))

    print(f"[p46] queue={len(rows)} critical={pc.get('CRITICAL',0)} high={pc.get('HIGH',0)} "
          f"medium={pc.get('MEDIUM',0)} low={pc.get('LOW',0)} validate={'PASS' if allok else 'FAIL'}", flush=True)


if __name__ == "__main__":
    main()
