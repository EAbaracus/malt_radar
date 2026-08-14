#!/usr/bin/env python3
"""P103 AUDIT — SMWS FIX-UP (read-only).
Repairs the list-set bug in SMWS per-file records, re-extracts all 41 sampled
SMWS PDFs with the frozen extractor, repairs per-file rows, and recomputes the
group aggregate honestly. Writes corpus_audit_enriched.json (audit dir only).
"""
import json, sqlite3, importlib.util
from pathlib import Path

BASE = Path(r"C:\Users\eltun\Documents\malt radar CLEAN")
OUT  = BASE / "mr-kep" / "p103_corpus_audit"
ENR  = OUT / "corpus_audit_enriched.json"
KDB  = BASE / "mr-kep" / "p102_bootstrap" / "knowledge.db"

import fitz
S01 = BASE / "mr-kep" / "book_enrichment_sprint01" / "enrich_mw_yearbook_2019.py"
spec = importlib.util.spec_from_file_location("enrich_s01", str(S01))
s01 = importlib.util.module_from_spec(spec); spec.loader.exec_module(s01)
load_lexicon    = s01.load_production_lexicon
extract_entities= s01.extract_entities
lexicon = load_lexicon(str(BASE/"output"/"import"/"production.db"))
_p = sqlite3.connect(f"file:{KDB}?mode=ro", uri=True)
COVERED = set(r[0] for r in _p.execute(
    "SELECT DISTINCT cn.whisky_id FROM canonical_vectors cv JOIN consensus_nodes cn ON cv.consensus_id=cn.consensus_id"))
_p.close()
# distilleries live in production.db, NOT knowledge.db
_p_pro = sqlite3.connect(f"file:{BASE/'output'/'import'/'production.db'}?mode=ro", uri=True)
DIST = {r[0].lower() for r in _p_pro.execute("SELECT DISTINCT name FROM distilleries") if r[0]}
_p_pro.close()
def is_dist(s):
    s=s.lower().strip(); return s in DIST or any(d in s for d in DIST if len(d)>6)

d = json.load(open(ENR))
sm = [r for r in d if r.get("group") == "SMWS (sampled)"]
agg = {"ent":0, "dist":0, "net":set()}
for r in sm:
    p = BASE / r["path"]
    doc = fitz.open(str(p)); n = len(doc)
    pages = [{"page_num": i+1, "text": doc[i].get_text()} for i in range(n)]
    doc.close()
    res = extract_entities(pages, lexicon)
    resolved = {e: v for e, v in res.items() if v.get("whisky_id")}
    wids = {v["whisky_id"] for v in resolved.values()}
    net = len(wids - COVERED)
    dist = sum(1 for e in res if not res[e].get("whisky_id") and is_dist(e))
    agg["ent"] += len(resolved); agg["dist"] += dist; agg["net"] |= (wids - COVERED)
    r["entities_est"] = len(resolved)
    r["distillery_ent_est"] = dist
    r["net_new_wids"] = net
    r["pages"] = n
    if "err" in (r.get("note") or ""):
        r["note"] = "re-extracted (list-set bug fixed)"
    r["meta_source"] = "embedded"
print(f"SMWS sampled={len(sm)} | resolved entities={agg['ent']} | distinct net-new={len(agg['net'])}")

# group record
grp = next((r for r in d if r.get("filename","").startswith("SMWS USA TASTING NOTES ARCHIVE (GROUP")), None)
if grp:
    grp["entities_est"] = agg["ent"]
    grp["distillery_ent_est"] = agg["dist"]
    grp["net_new_wids"] = len(agg["net"])
    grp["note"] = (f"RECOMPUTED over {len(sm)} sampled files (every 20th of "
                   f"{grp.get('pages')}). Net-new = distinct union across sample (floor); "
                   f"archive overlap is extreme, so full-803 gain ≈ this, not linear.")
    print("group updated:", {k: grp.get(k) for k in ("entities_est","net_new_wids")})

json.dump(d, open(ENR, "w"), indent=2, default=str)
print("Wrote", ENR)
