#!/usr/bin/env python
"""
P45 PHASE 5 — FLAVOR RADAR MAPPING
Reads:  output/import/smws/staging_smws_tasting_notes.csv
Writes: output/import/smws/flavor_radar.jsonl

For each staging record, score 7 Malt Radar axes (0..1) from the SMWS flavour
category + tasting-notes text using a transparent keyword lexicon. Also emit a
per-axis confidence. Heuristic only — consumed by human review, never auto-applied.

Axes: smoky, peaty, sherry, fruity, sweet, spicy, maritime
"""
import csv
import json
import re
from pathlib import Path

ROOT = Path(r"C:\Users\eltun\Documents\malt radar CLEAN")
IN = ROOT / "output/import/smws/staging_smws_tasting_notes.csv"
OUT = ROOT / "output/import/smws/flavor_radar.jsonl"

# keyword -> axis (+weight). Lowercase substring matching on normalized text.
LEX = {
    "smoky":  [("smok", 1.0), ("peat", 0.0), ("ash", 0.6), ("char", 0.7),
               ("campfire", 1.0), ("barbecue", 0.8), ("bbq", 0.8), ("tar", 0.7),
               ("medicinal", 0.6), ("islay", 0.5), ("coal", 0.7), ("cinder", 0.8)],
    "peaty":  [("peat", 1.0), ("smok", 0.4), ("turf", 0.9), ("bog", 0.8),
               ("moss", 0.6), ("medicinal", 0.5), ("kippery", 0.9), ("iodine", 0.7),
               ("maritime", 0.2)],
    "sherry": [("sherr", 1.0), ("oloroso", 1.0), ("oloros", 1.0), ("px", 0.6),
               ("pedro ximenez", 1.0), ("amontillado", 0.9), ("rake", 0.0),
               ("raisin", 0.7), ("dried fruit", 0.6), ("christmas cake", 0.8),
               ("date", 0.4), ("fig", 0.5), ("nutty", 0.5)],
    "fruity": [("fruit", 1.0), ("apple", 0.7), ("peach", 0.8), ("pear", 0.7),
               ("pineapple", 0.8), ("mango", 0.8), ("banana", 0.7), ("citrus", 0.7),
               ("lemon", 0.6), ("orange", 0.6), ("berry", 0.7), ("cherry", 0.7),
               ("plum", 0.7), ("apricot", 0.8), ("guava", 0.9), ("tropical", 0.9),
               ("melon", 0.7), ("pear", 0.0)],
    "sweet":  [("sweet", 1.0), ("honey", 0.8), ("sugar", 0.8), ("toffee", 0.8),
               ("caramel", 0.8), ("vanilla", 0.6), ("syrup", 0.8), ("fudge", 0.9),
               ("candy", 0.8), ("chocolate", 0.5), ("cream", 0.6), ("custard", 0.8),
               ("cake", 0.6), ("meringue", 0.8), ("icing", 0.8), ("sherbet", 0.6)],
    "spicy":  [("spic", 1.0), ("cinnamon", 0.8), ("ginger", 0.7), ("pepper", 0.7),
               ("clove", 0.8), ("nutmeg", 0.8), ("chilli", 0.8), ("chili", 0.8),
               ("anise", 0.8), ("liquorice", 0.7), ("licorice", 0.7), ("cardamom", 0.9),
               ("cassia", 0.9), ("paprika", 0.8), ("cumin", 0.8), ("prickly", 0.5)],
    "maritime":[("salt", 0.9), ("sea", 0.8), ("maritime", 1.0), ("coast", 0.8),
               ("brine", 0.9), ("oyster", 0.9), ("shellfish", 0.8), ("seaweed", 0.9),
               ("kelp", 0.9), ("wetsuit", 0.9), ("ferry", 0.5), ("coastal", 0.8),
               ("beach", 0.7), ("mineral", 0.4)],
}

# SMWS flavour-category strong priors
CAT_PRIOR = {
    "spicy": {"spicy": 0.6},
    "sweet": {"sweet": 0.6},
    "dry": {},
    "smoky": {"smoky": 0.6, "peaty": 0.3},
    "fruity": {"fruity": 0.6},
    "malty": {},
    "woody": {},
    "light": {},
    "oily": {},
}

def score_text(text):
    t = text.lower()
    scores = {k: 0.0 for k in LEX}
    hits = {k: 0 for k in LEX}
    for axis, kws in LEX.items():
        for kw, w in kws:
            if kw and kw in t:
                scores[axis] += w
                hits[axis] += 1
    return scores, hits

def main():
    if not IN.exists():
        raise SystemExit("missing staging csv; run stage4 first")
    rows = []
    with open(IN, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append(r)
    out = []
    for r in rows:
        notes = r.get("tasting_notes_raw", "") or ""
        fp = r.get("flavour_profile", "") or ""
        src = f"{notes} {fp}".strip()
        scores, hits = score_text(src)
        # apply category prior
        fl = fp.lower()
        for cat, prior in CAT_PRIOR.items():
            if cat in fl:
                for ax, v in prior.items():
                    scores[ax] = max(scores[ax], v)
        # normalize to 0..1 (cap at 1.0) and light floor so non-zero text isn't totally 0
        axes = {}
        conf = 0.0
        total_hits = sum(hits.values())
        for ax in LEX:
            s = min(scores[ax], 1.0)
            # scale: every 2 distinct keyword hits saturates the axis
            s = min(1.0, s * 0.6 + 0.0)  # weight base
            axes[ax] = round(s, 3)
        # confidence: more keyword evidence and longer notes => higher confidence
        conf = min(1.0, 0.3 + min(total_hits, 10) * 0.05 + min(len(notes), 800) / 4000.0)
        axes["confidence"] = round(conf, 3)
        out.append({
            "id": r.get("id"),
            "cask_no": r.get("cask_no"),
            "file_name": r.get("file_name"),
            "smoky": axes["smoky"], "peaty": axes["peaty"], "sherry": axes["sherry"],
            "fruity": axes["fruity"], "sweet": axes["sweet"], "spicy": axes["spicy"],
            "maritime": axes["maritime"], "confidence": axes["confidence"],
        })
    with open(OUT, "w", encoding="utf-8") as f:
        for o in out:
            f.write(json.dumps(o, ensure_ascii=False) + "\n")
    print(f"[phase5] wrote {len(out)} flavor records", flush=True)

if __name__ == "__main__":
    main()
