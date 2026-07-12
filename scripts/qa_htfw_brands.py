"""
PXX-HTFW-QA — Production-readiness quality gate for
htfw_world_whisky_brands_enriched.csv (Malt Radar).

Principle (per AGENTS.md + user directive):
  * READ-ONLY. No mutation of the CSV, no writes to any DB, no edits to
    import files. Analysis + reporting only.
  * Deterministic & reproducible: same input -> same output. No network,
    no clocks in logic, no randomness.

Checks (per spec):
  1. exact duplicate rows
  2. normalized-name duplicate (within enriched)
  3. slug duplicate
  4. htfw_url duplicate
  5. existing distillery/brand conflict
       - (5a) >=2 enriched rows map to the SAME repo whiskynet link
       - (5b) whisky-net link already present in repo distilleries.csv/brands.csv
              (reconciliation signal, NOT a hard fail by itself)
  6. entity_type conflict (row claimed distillery vs brand across sources,
     or ambiguous classification)
  7. country/owner inconsistency (cross-source: distilleries.csv vs brands.csv)
  8. required-field gaps (matched/brand_match must carry country+owner;
     all rows must carry name+slug+htfw_url)
  9. UTF-8 decode + CSV schema validation

Outputs:
  reports/htfw_qa_report.md
  reports/htfw_conflicts.csv
  reports/htfw_duplicates.csv
  reports/htfw_missing_fields.csv

Decision: GO | GO WITH MANUAL REVIEW | NO-GO
"""
import csv, os, re, sys, json
from collections import Counter, defaultdict, OrderedDict

BASE = r"C:\Users\eltun\Documents\malt radar CLEAN"
INPUT = os.path.join(BASE, "data", "input", "htfw_world_whisky_brands_enriched.csv")
DIST = os.path.join(BASE, "data", "books", "yeni veriler", "distilleries.csv")
BR = os.path.join(BASE, "data", "books", "yeni veriler", "brands.csv")
REP = os.path.join(BASE, "reports", "htfw_qa_report.md")
CONFLICTS = os.path.join(BASE, "reports", "htfw_conflicts.csv")
DUPS = os.path.join(BASE, "reports", "htfw_duplicates.csv")
MISSING = os.path.join(BASE, "reports", "htfw_missing_fields.csv")

EXPECTED_COLS = ["name", "owner", "country", "region", "location", "founded",
                 "total_production", "type", "status", "link", "entity_type",
                 "match_status", "match_source", "confidence", "htfw_url",
                 "slug", "letter"]


def norm(s):
    s = (s or "").lower().strip().replace("\u2019", "'")
    s = re.sub(r"^the\s+", "", s)
    s = re.sub(r",?\s*the$", "", s)
    for w in ["distillery", "distilleries", "distillers", "distiller", "co.", "co",
              "company", "ltd", "limited", "llc", "inc.", "inc", "plc",
              "corporation", "corp", "gmbh", "ab", "pvt. ltd.", "pvt ltd",
              "pty", "pvt", "s.a.", "sa", "ag", "srl", "bv", "nv", "spa", "kk",
              "co ltd"]:
        s = re.sub(r"\b" + re.escape(w) + r"\b", "", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def load_csv(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    errors = []          # hard blockers -> NO-GO
    warnings = []        # -> GO WITH MANUAL REVIEW
    conflicts = []        # -> reports/htfw_conflicts.csv
    duplicates = []       # -> reports/htfw_duplicates.csv
    missing = []          # -> reports/htfw_missing_fields.csv

    # ---- 9. UTF-8 + schema ----
    rows = load_csv(INPUT)
    cols = list(rows[0].keys()) if rows else []
    if cols != EXPECTED_COLS:
        errors.append(f"Schema mismatch: got {cols}, expected {EXPECTED_COLS}")
    n = len(rows)

    # ---- 1. exact duplicate rows ----
    seen = Counter(tuple(r.items()) for r in rows)
    for key, cnt in seen.items():
        if cnt > 1:
            nm = dict(key).get("name", "?")
            duplicates.append({"dup_type": "exact_row", "value": nm,
                               "count": cnt, "rows": nm})
            errors.append(f"Exact duplicate row for '{nm}' x{cnt}")

    # ---- 2. normalized name duplicate ----
    nn = defaultdict(list)
    for r in rows:
        nn[norm(r["name"])].append(r["name"])
    for k, vals in nn.items():
        if len(vals) > 1:
            duplicates.append({"dup_type": "normalized_name", "value": k,
                               "count": len(vals), "rows": " | ".join(vals)})
            errors.append(f"Normalized-name collision: {k} -> {vals}")

    # ---- 3. slug duplicate ----
    sl = Counter(r["slug"] for r in rows)
    for k, cnt in sl.items():
        if cnt > 1:
            duplicates.append({"dup_type": "slug", "value": k, "count": cnt,
                               "rows": k})
            errors.append(f"Slug duplicate: {k} x{cnt}")

    # ---- 4. htfw_url duplicate ----
    hu = Counter(r["htfw_url"] for r in rows)
    for k, cnt in hu.items():
        if cnt > 1:
            duplicates.append({"dup_type": "htfw_url", "value": k, "count": cnt,
                               "rows": k})
            errors.append(f"HTFW URL duplicate: {k} x{cnt}")

    # ---- 5. existing distillery/brand conflict ----
    dist_rows = load_csv(DIST)
    br_rows = load_csv(BR)
    dist_links = {r["link"].strip() for r in dist_rows}
    br_links = {r["link"].strip() for r in br_rows}
    dist_norm = {norm(r["name"]) for r in dist_rows}
    br_norm = {norm(r["name"]) for r in br_rows}

    # (5a) multiple enriched rows -> same repo link
    link_map = defaultdict(list)
    for r in rows:
        if r["match_status"] in ("matched", "brand_match") and r["link"] != "?":
            link_map[r["link"]].append(r["name"])
    for ln, names in link_map.items():
        if len(names) > 1:
            conflicts.append({"conflict_type": "same_repo_link_multiple_htfw",
                              "detail": ln, "entities": " | ".join(names)})
            errors.append(f"Multiple HTFW rows map to one repo link {ln}: {names}")

    # (5b) reconciliation signal: matched link already exists in repo
    already = 0
    for r in rows:
        if r["match_status"] in ("matched", "brand_match") and r["link"] != "?":
            if r["link"] in dist_links or r["link"] in br_links:
                already += 1
    if already:
        conflicts.append({"conflict_type": "reconciliation_already_in_repo",
                          "detail": f"{already} rows already present in repo data (by link)",
                          "entities": ""})
        warnings.append(f"{already} matched rows reference repo links already in distilleries.csv/brands.csv (expected reconciliation, review)")

    # ---- 6. entity_type conflict (symmetric) ----
    # A row classified differently than the repo's dominant classification,
    # or a 'new' row whose normalized name collides (substring) with a repo entity.
    substring_candidates = []
    # index repo by normalized name for symmetric lookup
    dist_by = {norm(r["name"]): r for r in dist_rows}
    br_by = {norm(r["name"]): r for r in br_rows}
    for r in rows:
        k = norm(r["name"])
        # (a) new row substring-collides with a repo entity (possible missed match)
        if r["match_status"] == "new" and k:
            hit = None
            for name_set, label in ((dist_norm, "distillery"), (br_norm, "brand")):
                for nm in name_set:
                    if nm and k and (k in nm or nm in k) and abs(len(k) - len(nm)) <= 8:
                        hit = (nm, label)
                        break
                if hit:
                    break
            if hit:
                substring_candidates.append((r["name"], hit[0], hit[1]))
                conflicts.append({"conflict_type": "entity_substring_vs_repo",
                                  "detail": f"{r['name']} ~ repo {hit[1]} '{hit[0]}'",
                                  "entities": r["name"]})
                warnings.append(f"New row '{r['name']}' substring-matches repo {hit[1]} '{hit[0]}' (possible missed match)")
        # (b) symmetric: repo has BOTH a distillery and a brand row for this name
        if k in dist_by and k in br_by:
            conflicts.append({"conflict_type": "entity_type_distillery_and_brand",
                              "detail": f"{r['name']} exists as both distillery and brand in repo",
                              "entities": r["name"]})
            warnings.append(f"{r['name']} exists as both distillery and brand in whiskynet (dual listing; see entity_type)")

    # ---- 7. country/owner inconsistency (cross-source) ----
    for r in rows:
        k = norm(r["name"])
        d = dist_by.get(k)
        b = br_by.get(k)
        if d and b:
            dc, bc = (d["country"] or "?"), (b.get("country") or "?")
            do, bo = (d["owner"] or "?"), (b.get("owner") or "?")
            if dc != bc or do != bo:
                conflicts.append({"conflict_type": "cross_source_inconsistency",
                                  "detail": f"{r['name']}: dist.country={dc} br.country={bc}; dist.owner={do} br.owner={bo}",
                                  "entities": r["name"]})
                warnings.append(f"Cross-source inconsistency for '{r['name']}' (country/owner differ distilleries.csv vs brands.csv)")

    # ---- 8. required-field gaps ----
    # Structural/identity fields are ALWAYS required (blocking if absent):
    STRUCTURAL = ["name", "slug", "htfw_url"]
    # Inherited-source fields are expected but may legitimately be '?' if the
    # upstream source (distilleries.csv / brands.csv) did not carry them, or if
    # the row is 'new' (never matched). Those are warnings, not blockers.
    MATCHED_INHERITED = ["owner", "country", "region", "location",
                         "founded", "type", "status"]
    for r in rows:
        struct_miss = [c for c in STRUCTURAL if not r[c].strip()]
        inherited_miss = []
        if r["match_status"] in ("matched", "brand_match"):
            inherited_miss = [c for c in MATCHED_INHERITED
                             if not r[c].strip() or r[c] == "?"]
        miss = struct_miss + inherited_miss
        if miss:
            missing.append({"name": r["name"], "match_status": r["match_status"],
                            "missing_fields": ", ".join(miss),
                            "severity": "blocker" if struct_miss else "warning"})
            if struct_miss:
                errors.append(f"Row '{r['name']}' missing structural field(s): {struct_miss}")
            else:
                warnings.append(f"Row '{r['name']}' ({r['match_status']}) has inherited '?' field(s): {inherited_miss} (upstream source gap)")

    # ---- write report CSVs ----
    _write_csv(DUPS, ["dup_type", "value", "count", "rows"], duplicates)
    _write_csv(CONFLICTS, ["conflict_type", "detail", "entities"], conflicts)
    _write_csv(MISSING, ["name", "match_status", "missing_fields", "severity"], missing)

    # ---- decision ----
    if errors:
        decision = "NO-GO"
    elif warnings:
        decision = "GO WITH MANUAL REVIEW"
    else:
        decision = "GO"

    matched = sum(1 for r in rows if r["match_status"] == "matched")
    brand_match = sum(1 for r in rows if r["match_status"] == "brand_match")
    new = sum(1 for r in rows if r["match_status"] == "new")

    report = _build_report(n, matched, brand_match, new, errors, warnings,
                            duplicates, conflicts, missing,
                            already, len(substring_candidates), decision,
                            len(missing))
    with open(REP, "w", encoding="utf-8") as f:
        f.write(report)

    print(report)
    print(f"\n[DECISION] {decision}")
    print(f"errors={len(errors)} warnings={len(warnings)} dups={len(duplicates)} conflicts={len(conflicts)} missing={len(missing)}")
    # deterministic exit code for CI: 0 always (report encodes decision); gate consumer reads DECISION
    return decision


def _write_csv(path, cols, data):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for d in data:
            w.writerow({c: d.get(c, "") for c in cols})


def _build_report(n, matched, brand_match, new, errors, warnings,
                  duplicates, conflicts, missing,
                  already, nsub, decision, nmiss):
    L = []
    L.append("# PXX-HTFW-QA — Production Quality Gate Report")
    L.append("")
    L.append(f"**Decision: {decision}**")
    L.append("")
    L.append("## Scope")
    L.append("- Target: `data/input/htfw_world_whisky_brands_enriched.csv`")
    L.append("- Mode: **READ-ONLY** — no data mutated, no DB/import writes.")
    L.append("- Deterministic: no network, no clock-dependent logic, no randomness.")
    L.append("")
    L.append("## Inventory")
    L.append(f"- Total rows: {n}")
    L.append(f"- matched (distillery, high confidence): {matched}")
    L.append(f"- brand_match (whiskynet brand, medium): {brand_match}")
    L.append(f"- new (unverified): {new}")
    L.append("")
    L.append("## Checks & Results")
    L.append("")
    L.append("| # | Check | Result |")
    L.append("|---|-------|--------|")
    L.append(f"| 1 | Exact duplicate rows | {'FAIL' if any(d['dup_type']=='exact_row' for d in duplicates) else 'PASS'} |")
    L.append(f"| 2 | Normalized-name duplicate | {'FAIL' if any(d['dup_type']=='normalized_name' for d in duplicates) else 'PASS'} |")
    L.append(f"| 3 | Slug duplicate | {'FAIL' if any(d['dup_type']=='slug' for d in duplicates) else 'PASS'} |")
    L.append(f"| 4 | HTFW URL duplicate | {'FAIL' if any(d['dup_type']=='htfw_url' for d in duplicates) else 'PASS'} |")
    L.append(f"| 5a | Same repo link for multiple HTFW rows | {'FAIL' if any(c['conflict_type']=='same_repo_link_multiple_htfw' for c in conflicts) else 'PASS'} |")
    L.append(f"| 5b | Reconciliation vs repo (matched already in repo) | {already} rows (review) |")
    L.append(f"| 6 | Entity-type conflict | {nsub} substring + {sum(1 for c in conflicts if c['conflict_type']=='entity_type_distillery_and_brand')} dual-listing (review) |")
    L.append(f"| 7 | Country/owner cross-source inconsistency | {sum(1 for c in conflicts if c['conflict_type']=='cross_source_inconsistency')} rows |")
    L.append(f"| 8 | Required-field gaps | {nmiss} rows |")
    L.append(f"| 9 | UTF-8 + schema validation | {'FAIL' if errors else 'PASS'} |")
    L.append("")
    L.append("## Blocking Errors (NO-GO causes)")
    if errors:
        for e in errors:
            L.append(f"- [BLOCKER] {e}")
    else:
        L.append("- None.")
    L.append("")
    L.append("## Warnings (Manual Review)")
    if warnings:
        for w in warnings:
            L.append(f"- {w}")
    else:
        L.append("- None.")
    L.append("")
    L.append("## Output Artifacts")
    L.append("- `reports/htfw_qa_report.md` (this file)")
    L.append("- `reports/htfw_conflicts.csv`")
    L.append("- `reports/htfw_duplicates.csv`")
    L.append("- `reports/htfw_missing_fields.csv`")
    L.append("")
    L.append("## Reproducibility")
    L.append("Run: `python scripts/qa_htfw_brands.py` (deterministic).")
    return "\n".join(L)


if __name__ == "__main__":
    main()
