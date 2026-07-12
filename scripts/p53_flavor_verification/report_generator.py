# =============================================================================
# P53 - Report Generator
# Consumes verify() outputs -> reports/p53/*.md + *.csv (deterministic).
# =============================================================================
import os
import csv
import json
from collections import Counter, defaultdict
import config.source_authority_matrix as M


def _write_csv(path, rows, fieldnames):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"wrote {os.path.basename(path)} ({len(rows)} rows)")


def generate(ledger, conflicts, manual, low_conf, tn_conflicts,
             missing, disagreements, batch_flags, impact):
    OUT = M.OUT_DIR
    os.makedirs(OUT, exist_ok=True)

    conf_counter = Counter(r["confidence"] for r in ledger)
    total = sum(conf_counter.values()) or 1
    fam_counter = Counter(r["authority_source"] for r in ledger)

    # ---- flavor_verification_summary.md ----
    lines = ["# Flavor Verification Summary (P53)\n",
             f"_Run date: {M.RUN_DATE}_\n",
             "\n## Scope\n",
             "Flavor profiles, tasting notes, and flavor-source provenance ONLY. "
             "Corporate/owner metadata out of scope (per P53 brief).\n",
             "\n## Headline metrics\n",
             "| Metric | Value |",
             "|---|---|",
             f"| Flavor ledger rows | {len(ledger)} |",
             f"| Flavor conflicts (X) | {len(conflicts)} |",
             f"| Manual review rows | {len(manual)} |",
             f"| Low-confidence flavor rows | {len(low_conf)} |",
             f"| Tasting-note flags (generic/short) | {len(tn_conflicts)} |",
             f"| Missing flavor profiles | {len(missing)} |",
             f"| Batch-policy divergences | {len(batch_flags)} |",
             f"| Source disagreements (low tier labelled high) | {len(disagreements)} |",
             f"| Recommendation neighbor rankings affected | {imp['neighbors_changed']} ({imp['pct_changed']}%) |\n",
             "\n## Confidence distribution (all flavor rows)\n",
             "| Level | Meaning | Count | % |",
             "|---|---|---|---|"]
    for lvl in ["A", "B", "C", "D", "E", "X"]:
        n = conf_counter.get(lvl, 0)
        lines.append(f"| {lvl} | {M.CONFIDENCE_LABELS[lvl]} | {n} | {100.0*n/total:.1f}% |")
    lines.append("\n## Source family distribution\n")
    lines.append("| Family | Rows |")
    lines.append("|---|---|")
    for s, n in fam_counter.most_common():
        lines.append(f"| {s} | {n} |")
    lines.append("\n## Recommendation impact (what-if)\n")
    lines.append(f"Under a confidence-weighted sensitivity model "
                 f"(low-confidence profiles down-weighted), **{imp['pct_changed']}%** "
                 f"of whisky similarity top-5 neighbor rankings would shift. "
                 f"This is a non-destructive analysis; production data is unchanged. "
                 f"See `similarity_impact_report.md` for examples.\n")
    lines.append("\n## Manual review required\n")
    lines.append(f"{len([m for m in manual if m.get('manual_review_required')=='true'])} "
                 "rows flagged `manual_review_required = true`. No automatic overwrite, "
                 "delete, or flavor synthesis performed (per P53 critical rule).\n")
    with open(os.path.join(OUT, "flavor_verification_summary.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("wrote flavor_verification_summary.md")

    # ---- flavor_conflicts.csv ----
    _write_csv(os.path.join(OUT, "flavor_conflicts.csv"),
               [{"entity": e, "entity_id": i, "entity_name": n, "field": fl,
                 "current_value": v, "authority_source": s, "note": nt}
                for (e, i, n, fl, v, s, nt) in conflicts],
               ["entity", "entity_id", "entity_name", "field", "current_value",
                "authority_source", "note"])

    # ---- tasting_note_conflicts.csv ----
    _write_csv(os.path.join(OUT, "tasting_note_conflicts.csv"),
               [{"entity_id": i, "entity_name": n, "part": p, "issue": iss,
                 "source": s, "excerpt": ex}
                for (i, n, p, iss, s, ex) in tn_conflicts],
               ["entity_id", "entity_name", "part", "issue", "source", "excerpt"])

    # ---- missing_flavor_profiles.csv ----
    _write_csv(os.path.join(OUT, "missing_flavor_profiles.csv"),
               [{"entity": m.get("entity"), "entity_id": m.get("entity_id"),
                 "entity_name": m.get("entity_name"), "field": m.get("field"),
                 "current_value": m.get("current_value"),
                 "authority_source": m.get("authority_source"), "note": m.get("note")}
                for m in missing],
               ["entity", "entity_id", "entity_name", "field", "current_value",
                "authority_source", "note"])

    # ---- low_confidence_flavors.csv ----
    _write_csv(os.path.join(OUT, "low_confidence_flavors.csv"), low_conf,
               ["entity_id", "entity_name", "field", "confidence",
                "authority_source", "data_confidence", "source_count", "note"])

    # ---- manual_review_queue.csv ----
    _write_csv(os.path.join(OUT, "manual_review_queue.csv"), manual,
               ["entity", "entity_id", "entity_name", "field", "current_value",
                "verification_status", "confidence", "authority_source", "note",
                "manual_review_required"])

    # ---- source_quality_report.md ----
    sf = Counter()
    for r in ledger:
        sf[M.source_family(r["authority_source"])[0]] += 1
    tier_counter = Counter()
    for r in ledger:
        fam, tier = M.source_family(r["authority_source"])
        tier_counter[tier] += 1
    slines = ["# Source Quality Report (P53)\n",
              f"_Run date: {M.RUN_DATE}_\n",
              "\nFlavor source priority (HIGHEST authority first), per P53 brief:\n",
              "1. WhiskyFun  2. Whisky Advocate  3. Official distillery  "
              "4. WhiskyNotes.be  5. The Whisky Edition  6. Master of Malt  "
              "7. The Whisky Exchange  8. NotebookLM  9. AI/rule-based\n",
              "\n## Rows by source family\n",
              "| Family | Rows |",
              "|---|---|"]
    for s, n in sf.most_common():
        slines.append(f"| {s} | {n} |")
    slines.append("\n## Rows by authority tier (1=best, 9=worst)\n")
    slines.append("| Tier | Rows |")
    slines.append("|---|---|")
    for t in sorted(tier_counter):
        slines.append(f"| {t} | {tier_counter[t]} |")
    slines.append("\n## Source disagreement (low-tier source asserting high confidence)\n")
    slines.append(f"{len(disagreements)} rows where an AI/rule-based (tier 9) source "
                  "carried a `high` confidence label. These are flagged X (conflict) "
                  "and NOT accepted as ground truth.\n")
    if disagreements:
        slines.append("| entity_id | name | field | claimed | expected | source |")
        slines.append("|---|---|---|---|---|---|")
        for (i, n, fl, c, exp, s, why) in disagreements[:50]:
            slines.append(f"| {i} | {n} | {fl} | {c} | {exp} | {s} |")
    slines.append("\n## Reassessment note\n")
    slines.append("The priority order should be revisited if a downstream audit shows "
                  "retailer (tier 6-7) or AI (tier 9) sources out-predict expert sources "
                  "(WhiskyFun/Advocate/Official). Current data does not yet support "
                  "promoting AI-derived flavor to trusted status.\n")
    with open(os.path.join(OUT, "source_quality_report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(slines) + "\n")
    print("wrote source_quality_report.md")

    # ---- similarity_impact_report.md ----
    ilines = ["# Similarity / Recommendation Impact Report (P53)\n",
              f"_Run date: {M.RUN_DATE}_\n",
              "\n**Analysis only** -- no production data modified.\n",
              "\n## Method\n",
              "Top-5 cosine neighbors were computed over the 7-axis `flavor_profile` "
              "for every whisky (current vectors), then recomputed after down-weighting "
              "low-confidence profiles (D=0.6, E=0.4, X=0.5). Rankings that change "
              "under this sensitivity model indicate fragility to flavor-data quality.\n",
              "\n## Result\n",
              "| Metric | Value |",
              "|---|---|",
              f"| Whiskies analysed | {imp['total']} |",
              f"| Neighbor rankings changed | {imp['neighbors_changed']} |",
              f"| % changed | {imp['pct_changed']}% |",
              "\n## Weight model\n",
              "```json\n" + json.dumps(imp["weight_model"], indent=2) + "\n```\n",
              "\n## Examples (before -> after top-3)\n",
              "| Whisky | Before | After |",
              "|---|---|---|"]
    nm = {r["entity_id"]: r["entity_name"] for r in ledger if r["entity"] == "flavor"}
    for (a, an, before, after) in imp["examples"][:40]:
        def names(lst):
            return ", ".join(nm.get(x, x) for x in lst)
        ilines.append(f"| {an} | {names(before)} | {names(after)} |")
    ilines.append("\n_If these weightings were adopted in production (separate, gated "
                  "pipeline), the above rankings would shift. This report does not "
                  "apply them._\n")
    with open(os.path.join(OUT, "similarity_impact_report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(ilines) + "\n")
    print("wrote similarity_impact_report.md")

    # ---- full P53 ledger (for traceability) ----
    _write_csv(os.path.join(OUT, "flavor_verification_ledger.csv"), ledger,
               ["entity", "entity_id", "entity_name", "field", "current_value",
                "verification_status", "confidence", "authority_source",
                "provenance", "last_verified", "note"])

    return conf_counter, fam_counter
