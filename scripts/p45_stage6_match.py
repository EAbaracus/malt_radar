#!/usr/bin/env python
"""
P45 PHASE 6 — MATCHING (suggestions ONLY, no mutation)
Reads (read-only): output/import/production.db  (whiskies, distilleries)
Reads:             output/import/smws/staging_smws_tasting_notes.csv
Writes:            output/reports/smws_match_preview.csv

Matching strategy:
  1) Distillery link: fuzzy-match the SMWS (inferred) distillery name against the
     `distilleries` table. This is the primary, high-value suggestion — it tells a
     reviewer which distillery entity a SMWS cask belongs to, WITHOUT creating rows.
  2) Duplicate awareness: fuzzy-match the inferred distillery + age + abv signature
     against existing `whiskies` to surface potential pre-existing records.
Rules:
  - fuzzy only, NO automatic merge, NO writes to production.
  - every row carries a 'suggestion' + 'needs_review' flag.
"""
import csv
import json
import re
import sqlite3
import difflib
from pathlib import Path

ROOT = Path(r"C:\Users\eltun\Documents\malt radar CLEAN")
PROD = ROOT / "output/import/production.db"
STAGE = ROOT / "output/import/smws/staging_smws_tasting_notes.csv"
OUT = ROOT / "output/reports/smws_match_preview.csv"

def load_production():
    uri = f"file:{PROD.as_posix()}?mode=ro"
    con = sqlite3.connect(uri, uri=True)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("SELECT distillery_id, name, region, country FROM distilleries")
    dists = cur.fetchall()
    # build name->row + a normalized list for matching
    dist_norm = {}
    for d in dists:
        nm = (d["name"] or "").strip()
        dist_norm[nm.lower()] = d
    cur.execute("SELECT whisky_id, name, original_name, distillery_id, region, age, abv FROM whiskies")
    wh = cur.fetchall()
    con.close()
    return dists, dist_norm, wh

def best_distillery_match(name, dists):
    if not name:
        return None, 0.0
    q = name.strip().lower()
    best = None
    best_score = 0.0
    for d in dists:
        dn = (d["name"] or "").strip().lower()
        if not dn:
            continue
        s = difflib.SequenceMatcher(None, q, dn).ratio()
        # token-based boost
        qt = set(re.findall(r"[a-z]+", q))
        dt = set(re.findall(r"[a-z]+", dn))
        if qt and dt:
            jac = len(qt & dt) / len(qt | dt)
            s = max(s, 0.6 * jac + 0.4 * s)
        if s > best_score:
            best_score = s
            best = d
    return best, round(best_score, 3)

def best_whisky_fuzzy(smws_dist, cask, age, abv, wh):
    """Conservative duplicate / coincidence surfacing.

    SMWS = single-cask independent bottlings. A true duplicate in production would be
    another record carrying the SAME cask code, OR a whisky whose name contains the
    exact SMWS cask code (prior SMWS import). We also surface a soft distillery
    coincidence only when the full SMWS distillery name appears as a whole word in the
    whisky name (avoids fragment false-positives like 'Glen' in 'golDen').

    Returns (dup_whisky_id, dup_whisky_name, dup_score, dup_reason).
    """
    if not cask:
        return None, "", 0.0, ""
    best_id = None; best_name = ""; best_score = 0.0; best_reason = ""
    # cask code must appear as a delimited token, not buried in a year/batch number
    cask_token = re.escape(cask).replace(r"\.", r"[.\s]") if cask else ""
    dist_tokens = set(re.findall(r"[A-Za-z]+", (smws_dist or "").lower()))
    for w in wh:
        wn = (w["name"] or "").lower()
        score = 0.0; reason = ""
        # 1) exact cask code as a standalone token AND distillery corroboration
        cask_hit = bool(cask_token) and bool(re.search(r"(?<!\d)" + cask_token + r"(?!\d)", wn))
        dist_hit = any(re.search(r"\b" + re.escape(t) + r"\b", wn) for t in dist_tokens if len(t) > 3)
        if cask_hit and dist_hit:
            score = 0.95; reason = "exact_cask_code_in_name"
        # 2) distillery-name-only coincidence (soft, < dup threshold)
        elif dist_hit:
            score = 0.5; reason = "distillery_name_match"
            try:
                if age and w["age"] is not None and int(age) == int(w["age"]): score += 0.2; reason += "+age"
            except Exception: pass
            try:
                if abv and w["abv"] is not None and abs(float(abv) - float(w["abv"])) < 0.5: score += 0.2; reason += "+abv"
            except Exception: pass
        if score > best_score:
            best_score = score; best_id = w["whisky_id"]; best_name = w["name"]; best_reason = reason
    return best_id, best_name, round(best_score, 3), best_reason

def main():
    if not STAGE.exists():
        raise SystemExit("missing staging csv; run stage4 first")
    dists, dist_norm, wh = load_production()
    rows = []
    with open(STAGE, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append(r)

    out_cols = ["file_name", "cask_no", "smws_distillery", "smws_region", "smws_age",
                "smws_abv", "matched_distillery_id", "matched_distillery_name",
                "matched_region", "distillery_score", "match_method",
                "dup_whisky_id", "dup_whisky_name", "dup_score", "dup_reason",
                "suggestion", "needs_review"]
    n_link = n_review = n_nomatch = n_dup = 0
    with open(OUT, "w", newline="", encoding="utf-8") as cf:
        w = csv.DictWriter(cf, fieldnames=out_cols)
        w.writeheader()
        for r in rows:
            sd = (r.get("distillery") or "").strip()
            age = r.get("age") or ""
            abv = r.get("abv") or ""
            md, score = best_distillery_match(sd, dists)
            # exact-name shortcut
            if sd and sd.lower() in dist_norm:
                md = dist_norm[sd.lower()]
                score = 1.0
            dup_id, dup_name, dup_score, dup_reason = best_whisky_fuzzy(sd, r.get("cask_no", ""), age, abv, wh)
            method = "exact" if score == 1.0 else "fuzzy"
            if score >= 0.85 and sd:
                suggestion = "LINK to existing distillery entity"
                needs = "no"
                n_link += 1
            elif score >= 0.6 and sd:
                suggestion = "REVIEW distillery link (moderate confidence)"
                needs = "yes"
                n_review += 1
            else:
                suggestion = "NO distillery match — verify SMWS cask code"
                needs = "yes"
                n_nomatch += 1
            if dup_id and float(dup_score) >= 0.75:
                suggestion += f"; POSSIBLE existing-whisky duplicate ({dup_reason})"
                n_dup += 1
                needs = "yes"
            w.writerow({
                "file_name": r.get("file_name", ""),
                "cask_no": r.get("cask_no", ""),
                "smws_distillery": sd,
                "smws_region": r.get("region", ""),
                "smws_age": age,
                "smws_abv": abv,
                "matched_distillery_id": (md["distillery_id"] if md else ""),
                "matched_distillery_name": (md["name"] if md else ""),
                "matched_region": (md["region"] if md else ""),
                "distillery_score": score,
                "match_method": method,
                "dup_whisky_id": (dup_id if dup_id else ""),
                "dup_whisky_name": dup_name,
                "dup_score": dup_score,
                "dup_reason": dup_reason,
                "suggestion": suggestion,
                "needs_review": needs,
            })
    print(f"[phase6] match preview written: link={n_link} review={n_review} nomatch={n_nomatch} dup_candidates={n_dup}", flush=True)

if __name__ == "__main__":
    main()
