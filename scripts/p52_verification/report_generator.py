# =============================================================================
# P52 - Report Generator
# -----------------------------------------------------------------------------
# Consumes verification_ledger.csv (produced by verification_engine.py) and the
# live DB, and emits the 9 required deliverable reports into reports/p52/.
#
# Reports:
#   verification_summary.md        - dashboard metrics + headline numbers
#   source_authority_matrix.md     - the documented authority chain per field
#   confidence_statistics.md       - confidence distribution (A/B/C/D/E/X)
#   field_coverage.md              - coverage by field + by entity
#   conflicts.csv                  - all X rows
#   missing_metadata.csv           - empty / no-verification-path rows
#   manual_review_queue.csv        - every row flagged for human review
#   source_disagreements.csv       - authoritative source vs source disagreements
#
# READ-ONLY on production.db (temp copy). Never writes production data.
# =============================================================================

import sqlite3
import csv
import os
import sys
import shutil
import tempfile
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import source_authority_matrix as M   # noqa: E402

OUT_DIR = M.OUTPUT_DIR
LEDGER = os.path.join(OUT_DIR, "verification_ledger.csv")

_LIVE = M.LIVE_DB
_TMP = None


def _db_copy():
    global _TMP
    if _TMP and os.path.exists(_TMP):
        return _TMP
    t = tempfile.NamedTemporaryFile(suffix=".db", delete=False, prefix="p52_rep_")
    t.close()
    shutil.copyfile(_LIVE, t.name)
    _TMP = t.name
    return _TMP


def read_ledger():
    return list(csv.DictReader(open(LEDGER, encoding="utf-8")))


def db_counts():
    con = sqlite3.connect(f"file:{_db_copy()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    c = {}
    for t in ["whiskies", "distilleries", "flavor_profiles", "tasting_notes"]:
        c[t] = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    con.close()
    return c


def main():
    rows = read_ledger()
    counts = db_counts()

    # ---- aggregate ----
    conf_counter = Counter(r["confidence"] for r in rows)
    status_counter = Counter(r["verification_status"] for r in rows)
    entity_counter = Counter(r["entity"] for r in rows)
    field_counter = Counter(r["field"] for r in rows)
    source_counter = Counter(r["authority_source"] for r in rows)
    review_rows = [r for r in rows if r["review_flag"] == "Y"]
    conflict_rows = [r for r in rows if r["confidence"] == "X"]
    missing_rows = [r for r in rows if r["verification_status"] == "unverified"
                    and r["note"] == "no_value"]
    # disagreements: extract from conflicts where note contains 'disagree'
    disagreements = [r for r in rows if "disagree" in r["note"]]

    # coverage by field (verified or not): count non-empty current_value
    cov_by_field = defaultdict(lambda: [0, 0])  # field -> [present, total]
    for r in rows:
        cov_by_field[r["field"]][1] += 1
        if r["current_value"] not in ("", None):
            cov_by_field[r["field"]][0] += 1

    # ---- 1. conflicts.csv ----
    _write_csv("conflicts.csv", rows=[dict(r) for r in conflict_rows],
               cols=["entity", "entity_id", "entity_name", "field",
                     "current_value", "authority_source", "note"])

    # ---- 2. missing_metadata.csv ----
    _write_csv("missing_metadata.csv", rows=missing_rows,
               cols=["entity", "entity_id", "entity_name", "field",
                     "confidence", "authority_source", "note"])

    # ---- 3. manual_review_queue.csv ----
    _write_csv("manual_review_queue.csv", rows=review_rows,
               cols=["entity", "entity_id", "entity_name", "field",
                     "current_value", "verification_status", "confidence",
                     "authority_source", "note"])

    # ---- 4. source_disagreements.csv ----
    _write_csv("source_disagreements.csv", rows=disagreements,
               cols=["entity", "entity_id", "entity_name", "field",
                     "current_value", "confidence", "authority_source", "note"])

    # ---- 5. field_coverage.md ----
    _write_field_coverage(cov_by_field, field_counter, counts)

    # ---- 6. confidence_statistics.md ----
    _write_confidence_stats(conf_counter, status_counter, source_counter)

    # ---- 7. source_authority_matrix.md ----
    _write_authority_matrix()

    # ---- 8. verification_summary.md ----
    _write_summary(counts, conf_counter, status_counter, entity_counter,
                   field_counter, source_counter, review_rows, conflict_rows,
                   missing_rows, disagreements)

    if _TMP and os.path.exists(_TMP):
        try:
            os.remove(_TMP)
        except OSError:
            pass


def _write_csv(name, rows, cols):
    p = os.path.join(OUT_DIR, name)
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"wrote {name}: {len(rows)} rows")


def _write_field_coverage(cov_by_field, field_counter, counts):
    p = os.path.join(OUT_DIR, "field_coverage.md")
    lines = ["# Field Coverage Report (P52)\n",
             f"_Run date: {M.RUN_DATE}_\n"]
    lines.append("\n## Records in scope\n")
    lines.append("| Entity | Count |")
    lines.append("|---|---|")
    for k in ["distilleries", "whiskies", "flavor_profiles", "tasting_notes"]:
        lines.append(f"| {k} | {counts[k]} |")
    lines.append("\n## Coverage by field\n")
    lines.append("Coverage = rows carrying a non-empty value / total verified fields.")
    lines.append("\n| Field | Present | Total | Coverage % |")
    lines.append("|---|---|---|---|")
    for f, (present, total) in sorted(cov_by_field.items(),
                                       key=lambda kv: kv[1][0] / max(kv[1][1], 1)):
        pct = 100.0 * present / total if total else 0
        lines.append(f"| {f} | {present} | {total} | {pct:.1f}% |")
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("wrote field_coverage.md")


def _source_family(src):
    """Collapse raw authority_source strings into reportable families."""
    s = (src or "").lower()
    if src == "official_source_references":
        return "official_source_references"
    if src == "ground_truth_seed":
        return "ground_truth_seed (A-tier curated)"
    if src == "legacy_repository":
        return "legacy_repository (no per-field provenance)"
    if "whisky advocate" in s:
        return "Whisky Advocate (book)"
    if "whiskeymapper" in s:
        return "WhiskeyMapper (model-derived)"
    if "notebooklm" in s or "book_notebooklm" in s:
        return "NotebookLM (AI)"
    if "rule_based" in s:
        return "rule_based extraction (AI)"
    if "structured_ml_whiskey" in s:
        return "ML match extraction (AI)"
    if "jim murray" in s or "whiskey opus" in s or "world atlas" in s \
            or "yearbook" in s or "anna" in s or "libgen" in s or "pdf" in s:
        return "book/reference (human-authored)"
    if "whiskyfun" in s or "whiskynotes" in s:
        return "web review (human-authored)"
    if "production_data.csv" in s:
        return "production_data.csv (legacy)"
    return "other_legacy_import"


def _write_confidence_stats(conf_counter, status_counter, source_counter):
    p = os.path.join(OUT_DIR, "confidence_statistics.md")
    # collapse authority sources into families
    fam = Counter()
    for s, n in source_counter.items():
        fam[_source_family(s)] += n
    lines = ["# Confidence Statistics Report (P52)\n",
             f"_Run date: {M.RUN_DATE}_\n",
             "\n## Confidence distribution (all field rows)\n",
             "\n| Level | Meaning | Count | % |",
             "|---|---|---|---|"]
    total = sum(conf_counter.values()) or 1
    for lvl in ["A", "B", "C", "D", "E", "X"]:
        n = conf_counter.get(lvl, 0)
        lines.append(f"| {lvl} | {M.CONFIDENCE_LABELS[lvl]} | {n} | {100.0*n/total:.1f}% |")
    lines.append(f"\n**Total field rows:** {total}\n")
    lines.append("\n## Verification status\n")
    lines.append("| Status | Count |")
    lines.append("|---|---|")
    for s, n in status_counter.most_common():
        lines.append(f"| {s} | {n} |")
    lines.append("\n## Authority source families\n")
    lines.append("Raw `authority_source` values are collapsed into families so the "
                 "breakdown is readable. Full per-row provenance is in "
                 "`verification_ledger.csv`.")
    lines.append("\n| Family | Field rows |")
    lines.append("|---|---|")
    for s, n in fam.most_common():
        lines.append(f"| {s} | {n} |")
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("wrote confidence_statistics.md")


def _write_authority_matrix():
    p = os.path.join(OUT_DIR, "source_authority_matrix.md")
    lines = ["# Source Authority Matrix (P52)\n",
             f"_Run date: {M.RUN_DATE}_\n",
             "\nThis matrix is the documented, deterministic basis for every "
             "verification decision.\n"]
    lines.append("\n## Confidence levels\n")
    lines.append("| Level | Meaning |")
    lines.append("|---|---|")
    for lvl in ["A", "B", "C", "D", "E", "X"]:
        lines.append(f"| {lvl} | {M.CONFIDENCE_LABELS[lvl]} |")
    lines.append("\n## Field authority chains (priority, top = most authoritative)\n")
    lines.append("| Field | Authority chain |")
    lines.append("|---|---|")
    for f, chain in M.FIELD_AUTHORITY_CHAIN.items():
        lines.append(f"| {f} | {' → '.join(chain)} |")
    lines.append("\n## Source tiers\n")
    lines.append("| Source | Tier |")
    lines.append("|---|---|")
    for s, t in sorted(M.SOURCE_TIER.items(), key=lambda kv: -kv[1]):
        lines.append(f"| {s} | {t} |")
    lines.append("\n## Manual-only sources (not auto-fetched this phase)\n")
    lines.append(", ".join(sorted(M.MANUAL_ONLY_SOURCES)))
    lines.append("\n## Seed ground truth (A-tier, curated)\n")
    lines.append(f"{len(M.GROUND_TRUTH)} canonical distilleries; "
                 f"{len(M.GROUND_TRUTH_ABV)} ABV reference expressions.")
    lines.append("\n> All seeds are stable, widely-documented facts about iconic "
                 "producers mapped to EXACT canonical distillery_id. They are the "
                 "automated verification backbone for the highest-value records and "
                 "are fully reviewable in `config/source_authority_matrix.py`.")
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("wrote source_authority_matrix.md")


def _write_summary(counts, conf_counter, status_counter, entity_counter,
                   field_counter, source_counter, review_rows, conflict_rows,
                   missing_rows, disagreements):
    p = os.path.join(OUT_DIR, "verification_summary.md")
    A = conf_counter.get("A", 0)
    B = conf_counter.get("B", 0)
    C = conf_counter.get("C", 0)
    D = conf_counter.get("D", 0)
    E = conf_counter.get("E", 0)
    X = conf_counter.get("X", 0)
    verified = A + B + C
    needs_review = len(review_rows)
    unknown = D + E
    total_rows = sum(conf_counter.values()) or 1
    lines = ["# Verification Summary (P52)\n",
             f"_Run date: {M.RUN_DATE} | Schema: {M.SCHEMA_VERSION}_\n",
             "_Mode: READ-ONLY. Production data was NOT modified. "
             "Every decision is reproducible from `verification_ledger.csv`._\n"]
    lines.append("\n## Dashboard metrics\n")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| Total distilleries | {counts['distilleries']} |")
    lines.append(f"| Total products (whiskies) | {counts['whiskies']} |")
    lines.append(f"| Flavor profiles | {counts['flavor_profiles']} |")
    lines.append(f"| Tasting notes records | {counts['tasting_notes']} |")
    lines.append(f"| Field rows verified (total) | {total_rows} |")
    lines.append(f"| Verified A (official) | {A} |")
    lines.append(f"| Verified B (2 sources agree) | {B} |")
    lines.append(f"| Verified C (1 trusted source) | {C} |")
    lines.append(f"| Verified A+B+C | {verified} |")
    lines.append(f"| Needs review (queue) | {needs_review} |")
    lines.append(f"| Conflicts (X) | {X} |")
    lines.append(f"| Unknown / legacy (D+E) | {unknown} |")
    pct = 100.0 * verified / total_rows
    lines.append(f"| Verified coverage % | {pct:.1f}% |")
    lines.append("\n## Top conflicting sources\n")
    # sources implicated in disagreements
    cs = Counter()
    for r in disagreements:
        cs[r["authority_source"]] += 1
    lines.append("| Source | Disagreements |")
    lines.append("|---|---|")
    for s, n in cs.most_common(10):
        lines.append(f"| {s} | {n} |")
    if not cs:
        lines.append("| (none) | 0 |")
    lines.append("\n## Most common missing metadata (empty, no verification path)\n")
    mc = Counter(r["field"] for r in missing_rows)
    lines.append("| Field | Empty rows |")
    lines.append("|---|---|")
    for f_, n in mc.most_common(15):
        lines.append(f"| {f_} | {n} |")
    lines.append("\n## Conflict breakdown by field\n")
    cf = Counter(r["field"] for r in conflict_rows)
    lines.append("| Field | Conflicts |")
    lines.append("|---|---|")
    for f_, n in cf.most_common():
        lines.append(f"| {f_} | {n} |")
    lines.append("\n## Notes\n")
    lines.append("- Conflicts are reported, never auto-resolved (per task spec).")
    lines.append("- A-tier seed covers 32 canonical distilleries + 20 ABV references.")
    lines.append("- Flavor 'high' labels on AI/rule-based sources are downgraded to "
                 "X (conflict) for manual review — see source_disagreements.csv.")
    lines.append("- Full per-field traceability: verification_ledger.csv.")
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("wrote verification_summary.md")


if __name__ == "__main__":
    main()
