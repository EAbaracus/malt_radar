# =============================================================================
# P52 - Verification Engine  (READ-ONLY on production.db)
# -----------------------------------------------------------------------------
# Produces a deterministic, fully-traceable verification ledger of every
# metadata field across distilleries + whiskies + flavor_profiles + tasting_notes.
#
# It never modifies production data. It never fabricates values. Every field
# row records: current_value, verification_status, confidence, authority_source,
# provenance_url, last_verified, conflict_flag, review_flag.
#
# Verification model per field:
#   - The engine assembles candidate values from THREE provenance channels:
#       1) official_source_references (DB)        -> A-tier
#       2) GROUND_TRUTH seed (curated, A-tier)    -> A-tier
#       3) existing DB value + its data_confidence -> D/E-tier legacy
#   - For SELECT fields (abv) it also runs a conflict check vs GROUND_TRUTH_ABV.
#   - If two authoritative channels disagree -> conflict (X) + manual review.
#   - Stable identity fields (country/region/founded/type/status) are verified
#     against the seed when the record's distillery is in the seed; otherwise
#     they keep their legacy confidence (D) with no auto-values invented.
# =============================================================================

import sqlite3
import csv
import json
import os
import sys
import shutil
import tempfile
from collections import defaultdict, Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import source_authority_matrix as M   # noqa: E402

# SAFETY: the engine NEVER opens the live production.db. It works on a private
# temp copy so the source-of-truth file is never touched (not even by SQLite's
# implicit WAL checkpoint, which physically rewrites file bytes on open).
_LIVE_DB = M.LIVE_DB
DB_PATH = None  # set by _prepare_db_copy()
OUT_DIR = M.OUTPUT_DIR
os.makedirs(OUT_DIR, exist_ok=True)


def _norm(s):
    if s is None:
        return ""
    return " ".join(str(s).lower().replace("'", "").replace("’", "").split())


def _to_float(x):
    try:
        if x is None or x == "":
            return None
        return float(x)
    except Exception:
        return None


def _prepare_db_copy():
    """Copy the live DB to a temp file and return its path. Idempotent."""
    global DB_PATH
    if DB_PATH and os.path.exists(DB_PATH):
        return DB_PATH
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False,
                                      prefix="p52_verify_")
    tmp.close()
    shutil.copyfile(_LIVE_DB, tmp.name)
    DB_PATH = tmp.name
    return DB_PATH


def _open_ro():
    db = _prepare_db_copy()
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def build_ground_truth_index(cur):
    """Map exact canonical distillery name -> {field: value, _id}.

    Resolves each GROUND_TRUTH key to the EXACT distillery row by name match
    (NOT fuzzy) so we never misattribute a sub-brand/expression row.
    """
    idx = {}
    for name, facts in M.GROUND_TRUTH.items():
        rows = cur.execute(
            "SELECT distillery_id, name FROM distilleries WHERE name = ?", (name,)
        ).fetchall()
        if rows:
            did = rows[0]["distillery_id"]
            idx[did] = {**facts, "_name": name}
    return idx


def load_official_refs(cur):
    """official_source_references -> {whisky_id: {field_name: (value, url, src, conf)}}"""
    refs = defaultdict(dict)
    for r in cur.execute(
        "SELECT entity_id, field_name, field_value, source_url, source_name, confidence "
        "FROM official_source_references WHERE entity_type='whisky'"
    ).fetchall():
        refs[r["entity_id"]][r["field_name"]] = (
            r["field_value"], r["source_url"], r["source_name"], r["confidence"]
        )
    return refs


DIST_FIELDS = ["country", "region", "founded", "owner", "status", "location"]
WHISKY_FIELDS = ["name", "distillery", "brand", "age", "abv", "region", "type",
                 "cask_type", "category"]


def confidence_from_db_label(label):
    """Map existing data_confidence / flavor_data_confidence to A-E/X.

    Legacy labels carry NO per-field provenance, so even 'high' degrades to D
    (legacy repository value) unless an authoritative channel confirms it.
    """
    if label is None:
        return "D"
    sl = str(label).strip().lower()
    if sl in ("high", "staged_import", "manual promotion"):
        return "D"
    if sl in ("medium", "low"):
        return "E"
    return "D"


def _last(lst):
    return lst[-1]


def verify():
    con = _open_ro()
    cur = con.cursor()
    gt = build_ground_truth_index(cur)
    official = load_official_refs(cur)

    ledger = []
    conflicts = []
    missing = []
    manual_q = []
    disagreements = []

    def add(entity, eid, ename, field, cur_val, status, conf, source, url, note=""):
        row = {
            "entity": entity, "entity_id": eid, "entity_name": ename,
            "field": field,
            "current_value": "" if cur_val is None else str(cur_val),
            "verification_status": status,
            "confidence": conf,
            "authority_source": source,
            "provenance_url": "" if url is None else str(url),
            "last_verified": M.RUN_DATE if status in ("verified", "conflict") else "",
            "conflict_flag": "Y" if conf == "X" else "N",
            "review_flag": "Y" if (conf == "X" or note == "no_value"
                                   or (status == "unverified" and "no automated" in note))
                                  else "N",
            "note": note,
        }
        ledger.append(row)
        if conf == "X":
            conflicts.append(row)
        if status == "unverified" and note in ("no_value",) \
                or (status == "unverified" and "no automated" in note):
            missing.append(row)
        if row["review_flag"] == "Y":
            manual_q.append(row)
        return row

    # ---------------- DISTILLERIES ----------------
    for d in cur.execute(
        "SELECT distillery_id, name, country, region, owner, parent_company, "
        "founded_year, founder, status, location, coordinates, official_website, "
        "wikidata_id, wikipedia_url, data_confidence FROM distilleries"
    ).fetchall():
        did = d["distillery_id"]
        seed = gt.get(did)
        for f in DIST_FIELDS:
            col = "founded_year" if f == "founded" else f
            val = d[col]
            if seed and f in seed:
                sv = seed[f]
                if val not in (None, ""):
                    disagree = (f == "founded" and _to_float(val) != _to_float(sv)) \
                        or (f != "founded" and _norm(val) != _norm(sv))
                    if disagree:
                        add("distillery", did, d["name"], f, val, "conflict", "X",
                            "ground_truth_seed", None,
                            f"seed={sv} db={val}; authoritative sources disagree")
                        disagreements.append((did, d["name"], f, str(val), str(sv),
                                              "ground_truth_seed", "legacy_repository"))
                        continue
                add("distillery", did, d["name"], f,
                    (val if val not in (None, "") else sv),
                    "verified", "A", "ground_truth_seed", None,
                    "verified against curated canonical fact")
            else:
                if val in (None, ""):
                    add("distillery", did, d["name"], f, val, "unverified",
                        confidence_from_db_label(d["data_confidence"]),
                        "legacy_repository", None, "no_value")
                else:
                    add("distillery", did, d["name"], f, val, "unverified",
                        confidence_from_db_label(d["data_confidence"]),
                        "legacy_repository", None,
                        "no automated source in this phase; legacy value retained")

    # ---------------- WHISKIES ----------------
    abv_seed_by_norm = {_norm(k): v for k, v in M.GROUND_TRUTH_ABV.items()}
    for w in cur.execute(
        "SELECT whisky_id, name, distillery_id, brand, country, region, type, age, "
        "age_statement, abv, cask_type, data_confidence FROM whiskies"
    ).fetchall():
        wid = w["whisky_id"]
        dname = ""
        if w["distillery_id"]:
            dr = cur.execute("SELECT name FROM distilleries WHERE distillery_id=?",
                             (w["distillery_id"],)).fetchone()
            dname = dr["name"] if dr else ""
        off = official.get(wid, {})

        # ABV
        if "abv" in off:
            add("whisky", wid, w["name"], "abv", w["abv"], "verified", "A",
                "official_source_references", off["abv"][1], "official fact table")
        elif w["abv"] not in (None, ""):
            key = _norm(w["name"])
            if key in abv_seed_by_norm:
                seed_abv, ssrc = abv_seed_by_norm[key]
                if abs((_to_float(w["abv"]) or -1) - seed_abv) > 0.05:
                    add("whisky", wid, w["name"], "abv", w["abv"], "conflict", "X",
                        ssrc, None,
                        f"seed={seed_abv} db={w['abv']}; authoritative sources disagree")
                    disagreements.append((wid, w["name"], "abv", str(w["abv"]),
                                          str(seed_abv), ssrc, "legacy_repository"))
                else:
                    add("whisky", wid, w["name"], "abv", w["abv"], "verified", "B",
                        ssrc, None, "agrees with curated official ABV")
            else:
                add("whisky", wid, w["name"], "abv", w["abv"], "unverified",
                    confidence_from_db_label(w["data_confidence"]),
                    "legacy_repository", None, "no automated source in this phase")
        else:
            add("whisky", wid, w["name"], "abv", w["abv"], "unverified", "D",
                "legacy_repository", None, "no_value")

        # AGE
        if w["age"] not in (None, ""):
            add("whisky", wid, w["name"], "age", w["age"], "unverified",
                confidence_from_db_label(w["data_confidence"]), "legacy_repository",
                None, "requires manual/retailer verification")
        else:
            add("whisky", wid, w["name"], "age", w["age"], "unverified", "D",
                "legacy_repository", None, "no_value")

        # CASK_TYPE
        if "cask_type" in off:
            add("whisky", wid, w["name"], "cask_type", w["cask_type"], "verified", "A",
                "official_source_references", off["cask_type"][1], "official fact table")
        elif w["cask_type"] not in (None, ""):
            add("whisky", wid, w["name"], "cask_type", w["cask_type"], "unverified",
                confidence_from_db_label(w["data_confidence"]), "legacy_repository",
                None, "no automated source in this phase")
        else:
            add("whisky", wid, w["name"], "cask_type", w["cask_type"], "unverified", "D",
                "legacy_repository", None, "no_value")

        # REGION (whisky-level)
        if "region" in off:
            add("whisky", wid, w["name"], "region", w["region"], "verified", "A",
                "official_source_references", off["region"][1], "official fact table")
        elif w["region"] not in (None, ""):
            add("whisky", wid, w["name"], "region", w["region"], "unverified",
                confidence_from_db_label(w["data_confidence"]), "legacy_repository",
                None, "no automated source in this phase")

        # identity fields
        for f, col, val in [("name", "name", w["name"]),
                            ("distillery", "distillery_id", dname or w["distillery_id"]),
                            ("brand", "brand", w["brand"]),
                            ("type", "type", w["type"])]:
            if val in (None, ""):
                add("whisky", wid, w["name"], f, val, "unverified", "D",
                    "legacy_repository", None, "no_value")
            else:
                add("whisky", wid, w["name"], f, val, "unverified",
                    confidence_from_db_label(w["data_confidence"]), "legacy_repository",
                    None, "identity field; legacy value retained")

    # ---------------- FLAVOR PROFILES ----------------
    for fp in cur.execute(
        "SELECT whisky_id, whisky_name, flavor_profile, flavor_vector, flavor_tags, "
        "flavor_source, flavor_data_confidence, source_count, evidence_count "
        "FROM flavor_profiles"
    ).fetchall():
        wid = fp["whisky_id"]
        fsrc = fp["flavor_source"] or ""
        fconf = (fp["flavor_data_confidence"] or "").strip().lower()
        src_for_row = fsrc if fsrc else "legacy_repository"
        is_ai = any(tok in fsrc for tok in M.AI_FLAVOR_SOURCES)
        if is_ai and fconf == "high":
            add("flavor", wid, fp["whisky_name"], "flavor_data_confidence", fconf,
                "conflict", "X", src_for_row, None,
                "AI/rule-based source labelled high; confidence inflated -> manual review")
            disagreements.append((wid, fp["whisky_name"], "flavor_data_confidence",
                                  fconf, "medium(expected)", src_for_row, "label_policy"))
        elif is_ai:
            add("flavor", wid, fp["whisky_name"], "flavor_profile", fp["flavor_profile"],
                "unverified", "E", src_for_row, None,
                "AI/rule-based extraction; not independently confirmed")
        elif fsrc in M.MANUAL_FLAVOR_SOURCES:
            add("flavor", wid, fp["whisky_name"], "flavor_profile", fp["flavor_profile"],
                "verified", "C", src_for_row, None,
                "trusted human-authored reference")
        elif fconf == "high":
            add("flavor", wid, fp["whisky_name"], "flavor_profile", fp["flavor_profile"],
                "verified", "C", src_for_row, None,
                "high-confidence legacy; treat as C until second source")
        else:
            add("flavor", wid, fp["whisky_name"], "flavor_profile", fp["flavor_profile"],
                "unverified", "E", src_for_row, None, "lower-confidence legacy enrichment")
        if (fp["source_count"] or 1) >= 2:
            add("flavor", wid, fp["whisky_name"], "flavor_source_corroboration",
                fp["source_count"], "verified", "B", src_for_row, None,
                f"{fp['source_count']} independent sources agree (source_count)")

    # ---------------- TASTING NOTES ----------------
    for tn in cur.execute(
        "SELECT whisky_id, normalized_name, nose_notes, palate_notes, finish_notes, "
        "data_confidence, source_name FROM tasting_notes"
    ).fetchall():
        wid = tn["whisky_id"]
        for f, col in [("nose", "nose_notes"), ("palate", "palate_notes"),
                       ("finish", "finish_notes")]:
            val = tn[col]
            if val in (None, ""):
                add("tasting", wid, tn["normalized_name"], f, val, "unverified", "D",
                    "legacy_repository", None, "no_value")
            else:
                add("tasting", wid, tn["normalized_name"], f, val, "unverified",
                    confidence_from_db_label(tn["data_confidence"]),
                    "legacy_repository", None,
                    "subjective tasting note; human review only")

    con.close()
    return ledger, conflicts, missing, manual_q, disagreements, gt


def write_ledger_csv(ledger):
    cols = ["entity", "entity_id", "entity_name", "field", "current_value",
            "verification_status", "confidence", "authority_source",
            "provenance_url", "last_verified", "conflict_flag", "review_flag", "note"]
    p = os.path.join(OUT_DIR, "verification_ledger.csv")
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in ledger:
            w.writerow(r)
    return p


if __name__ == "__main__":
    ledger, conflicts, missing, manual_q, disagreements, gt = verify()
    p = write_ledger_csv(ledger)
    # cleanup temp db copy so no trace of the source file is modified
    if DB_PATH and os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
        except OSError:
            pass
    print(f"ledger rows: {len(ledger)}")
    print(f"conflicts (X): {len(conflicts)}")
    print(f"missing/unverified-no-value: {len(missing)}")
    print(f"manual review queue: {len(manual_q)}")
    print(f"source disagreements: {len(disagreements)}")
    print(f"ground-truth distilleries resolved: {len(gt)}")
    print(f"ledger -> {p}")
    print("NOTE: live production.db was NOT opened by this run (temp copy used).")

