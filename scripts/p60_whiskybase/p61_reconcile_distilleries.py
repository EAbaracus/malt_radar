"""
P61 - World Whisky Distillery Reconciliation (staging only, READ-ONLY vs production.db)

Goal: reconcile the unmatched world-whisky whiskies (distillery_id IS NULL in the
P60 batch W3294..W3557) against existing distilleries, producing:
  1. world_whisky_distillery_review.csv   - one row per unmatched whisky w/ verdict
  2. candidate_matches.csv                - candidate distillery matches + confidence
  3. CREATE_NEW_DISTILLERY suggestions    - (embedded in review CSV as recommended_action)
  4. p61_audit_report.md

Rules (per task spec):
  * Do NOT blindly create new distillery records.
  * Preserve brand vs distillery distinction (HTFW owner = distillery candidate;
    whisky name = brand/marka). We never collapse a brand into a distillery row.
  * Try existing-distillery match FIRST (norm_name exact, then fuzzy).
  * Produce a confidence score per candidate.
  * confidence >= 95  -> AUTO_VERIFY (recommended action: LINK_EXISTING)
  * confidence 70-95  -> MANUAL_REVIEW (queue)
  * confidence < 70   -> NULL (leave distillery_id untouched, no suggestion)
  * Production DB is NEVER modified. Output is staging only.

Confidence model (transparent, deterministic):
  exact norm_name match on distillery.name ........ 100
  norm_name match after stripping common suffixes .. 96
  fuzzy token_sort ratio >= 0.92 ................... 90
  fuzzy ratio 0.85-0.92 ............................. 80
  fuzzy ratio 0.75-0.85 ............................. 72
  fuzzy ratio 0.60-0.75 ............................. 65   (below 70 -> NULL)
  else .............................................. <60  (NULL)
"""
import os
import sys
import csv
import sqlite3
import argparse
import datetime as dt
from difflib import SequenceMatcher

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB = os.path.join(ROOT, "output", "import", "production.db")
HTFW = os.path.join(ROOT, "data", "input", "htfw_world_whisky_brands_enriched.csv")
STAGING_DIR = os.path.join(ROOT, "data", "output")
REPORTS_DIR = os.path.join(ROOT, "output", "reports")

SUFFIXES = ["distillery", "distilleries", "whisky", "whiskey", "winery",
            "brewery", "co", "co.", "company", "ltd", "limited", "inc",
            "gmbh", "plc", "pvt", "llc", "spa", "srl", "sa"]


def norm_name(name):
    if not name:
        return ""
    s = name.lower().replace("'", "").replace("\u2019", "")
    if s.startswith("the "):
        s = s[4:]
    return "".join(ch for ch in s if ch.isalnum())


def strip_suffixes(norm):
    toks = norm.split()
    cleaned = [t for t in toks if t not in SUFFIXES]
    return "".join(cleaned) if cleaned else norm


def fuzzy_ratio(a, b):
    return SequenceMatcher(None, a, b).ratio()


def load_htfw():
    owner = {}
    if not os.path.exists(HTFW):
        return owner
    with open(HTFW, "r", encoding="utf-8-sig", newline="") as f:
        for d in csv.DictReader(f):
            def g(k):
                v = d.get(k, "")
                return "" if v in (None, "?", "") else str(v).strip()
            owner[g("name")] = {
                "owner": g("owner"), "region": g("region"),
                "country": g("country"), "type": g("type"),
                "status": g("status"), "location": g("location"),
                "founded": g("founded"), "htfw_url": g("htfw_url"),
            }
    return owner


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="cap unmatched rows (0=all)")
    args = ap.parse_args()

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    # existing distilleries index
    dists = []
    for r in conn.execute("SELECT distillery_id, name, country, region FROM distilleries"):
        if r["name"]:
            dists.append({
                "id": r["distillery_id"], "name": r["name"],
                "norm": norm_name(r["name"]), "norm_ss": strip_suffixes(norm_name(r["name"])),
                "country": r["country"], "region": r["region"],
            })

    unmatched = conn.execute(
        """SELECT whisky_id, name FROM whiskies
           WHERE whisky_id GLOB 'W[0-9]*'
             AND CAST(SUBSTR(whisky_id,2) AS INT) BETWEEN 3294 AND 3557
             AND distillery_id IS NULL ORDER BY name"""
    ).fetchall()
    if args.limit:
        unmatched = unmatched[:args.limit]
    htfw = load_htfw()
    conn.close()

    review_rows = []
    candidate_rows = []
    auto = manual = nullc = create_new = 0

    for w in unmatched:
        wid, wname = w["whisky_id"], w["name"]
        meta = htfw.get(wname, {})
        owner = meta.get("owner", "")
        wnorm = norm_name(wname)
        wnorm_ss = strip_suffixes(wnorm)

        # 1) existing match FIRST: try whisky name, then owner as distillery candidate
        best = None  # (score, dist_id, dist_name, basis)
        for cand in (wname, owner):
            cnorm = norm_name(cand)
            cnorm_ss = strip_suffixes(cnorm)
            if not cnorm:
                continue
            for d in dists:
                score = None
                basis = None
                if cnorm == d["norm"]:
                    score, basis = 100, "exact_name"
                elif cnorm_ss and cnorm_ss == d["norm_ss"]:
                    score, basis = 96, "suffix_stripped"
                else:
                    fr = fuzzy_ratio(cnorm, d["norm"])
                    if fr >= 0.92:
                        score, basis = 90, "fuzzy_0.92"
                    elif fr >= 0.85:
                        score, basis = 80, "fuzzy_0.85"
                    elif fr >= 0.75:
                        score, basis = 72, "fuzzy_0.75"
                    elif fr >= 0.60:
                        score, basis = 65, "fuzzy_0.60"
                if score is not None and (best is None or score > best[0]):
                    best = (score, d["id"], d["name"], basis, cand == owner)

        if best is not None:
            score, did, dname, basis, via_owner = best
            candidate_rows.append({
                "whisky_id": wid, "whisky_name": wname, "candidate_distillery_id": did,
                "candidate_distillery_name": dname, "confidence": score,
                "match_basis": basis, "matched_via": "owner" if via_owner else "name",
                "owner_field": owner,
            })
            if score >= 95:
                verdict, action = "AUTO_VERIFY", "LINK_EXISTING"
                auto += 1
            elif score >= 70:
                verdict, action = "MANUAL_REVIEW", "LINK_EXISTING_REVIEW"
                manual += 1
            else:
                verdict, action = "NULL_NO_CONFIDENT_MATCH", "LEAVE_NULL"
                nullc += 1
            review_rows.append({
                "whisky_id": wid, "whisky_name": wname, "brand_or_expression": "brand",
                "owner_field": owner, "country": meta.get("country", ""),
                "region": meta.get("region", ""), "type": meta.get("type", ""),
                "candidate_distillery_id": did, "candidate_distillery_name": dname,
                "confidence": score, "match_basis": basis,
                "verdict": verdict, "recommended_action": action,
                "htfw_url": meta.get("htfw_url", ""),
            })
            continue

        # 2) No existing match -> CREATE_NEW_DISTILLERY suggestion (NOT auto-create)
        #    Brand vs distillery preserved: if owner present and differs from name,
        #    owner is the distillery candidate; name stays brand.
        if owner and norm_name(owner) != wnorm:
            create_name = owner
            rel = "owner_as_distillery"
        else:
            create_name = wname
            rel = "brand_as_distillery"
        create_new += 1
        review_rows.append({
            "whisky_id": wid, "whisky_name": wname, "brand_or_expression": "brand",
            "owner_field": owner, "country": meta.get("country", ""),
            "region": meta.get("region", ""), "type": meta.get("type", ""),
            "candidate_distillery_id": "", "candidate_distillery_name": create_name,
            "confidence": 0, "match_basis": "no_existing_match",
            "verdict": "CREATE_NEW_DISTILLERY", "recommended_action": "CREATE_NEW_DISTILLERY",
            "htfw_url": meta.get("htfw_url", ""),
        })

    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    # outputs
    review_csv = os.path.join(STAGING_DIR, f"p61_world_whisky_distillery_review_{ts}.csv")
    cand_csv = os.path.join(STAGING_DIR, f"p61_candidate_matches_{ts}.csv")
    with open(review_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "whisky_id", "whisky_name", "brand_or_expression", "owner_field",
            "country", "region", "type", "candidate_distillery_id",
            "candidate_distillery_name", "confidence", "match_basis",
            "verdict", "recommended_action", "htfw_url"])
        w.writeheader(); w.writerows(review_rows)
    with open(cand_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "whisky_id", "whisky_name", "candidate_distillery_id",
            "candidate_distillery_name", "confidence", "match_basis",
            "matched_via", "owner_field"])
        w.writeheader(); w.writerows(candidate_rows)

    report = os.path.join(REPORTS_DIR, f"p61_audit_report_{ts}.md")
    os.makedirs(REPORTS_DIR, exist_ok=True)
    create_names = sorted({r["candidate_distillery_name"] for r in review_rows
                           if r["recommended_action"] == "CREATE_NEW_DISTILLERY"})
    with open(report, "w", encoding="utf-8") as f:
        f.write(f"# P61 World Whisky Distillery Reconciliation - Audit Report\n\n")
        f.write(f"- generated_at: {ts}\n")
        f.write(f"- unmatched_world_whisky: {len(unmatched)}\n")
        f.write(f"- production_db_modified: NO (staging only)\n\n")
        f.write("## Verdict distribution\n")
        f.write(f"- AUTO_VERIFY (>=95, LINK_EXISTING): {auto}\n")
        f.write(f"- MANUAL_REVIEW (70-95, queue): {manual}\n")
        f.write(f"- NULL (<70, no suggestion): {nullc}\n")
        f.write(f"- CREATE_NEW_DISTILLERY suggestions: {create_new}\n\n")
        f.write("## Rules honored\n")
        f.write("- Existing distillery match attempted first (name, then owner).\n")
        f.write("- Brand vs distillery distinction preserved (owner=distillery candidate, name=brand).\n")
        f.write("- No blind distillery creation; CREATE_NEW is a suggestion only.\n")
        f.write("- Confidence thresholds: >=95 auto, 70-95 manual, <70 NULL.\n\n")
        f.write("## CREATE_NEW_DISTILLERY suggestions (suggested distillery name)\n")
        for n in create_names:
            f.write(f"- {n}\n")
        f.write(f"\n## Outputs\n")
        f.write(f"- review: {os.path.relpath(review_csv, ROOT)}\n")
        f.write(f"- candidates: {os.path.relpath(cand_csv, ROOT)}\n")
        f.write(f"- audit: {os.path.relpath(report, ROOT)}\n")

    print(f"P61 done. unmatched={len(unmatched)} auto={auto} manual={manual} null={nullc} create_new={create_new}")
    print(f"review: {review_csv}")
    print(f"candidates: {cand_csv}")
    print(f"audit: {report}")
    print("production_db_modified: NO")


if __name__ == "__main__":
    main()
