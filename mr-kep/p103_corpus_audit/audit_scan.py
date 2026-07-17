#!/usr/bin/env python3
"""
P103 CORPUS AUDIT — COMPLETE READ-ONLY REASSESSMENT (fitz rewrite)
STRICTLY READ-ONLY: production.db & knowledge.db opened ?mode=ro. No writes/commits/renames.
Entity estimates use the FROZEN Sprint-01 extractor against production lexicon (import-only).
Large PDFs: SAMPLED (page-cap stride) for estimate; full re-read happens in real sprints.
SMWS group: SAMPLED every 20th file, group estimate scaled to 803 (labelled).
Records written incrementally + checkpoint every 50 files (timeout insurance).
"""
import os, sys, json, hashlib, sqlite3, importlib.util, re
from pathlib import Path

BASE = Path(r"C:\Users\eltun\Documents\malt radar CLEAN")
OUT  = BASE / "mr-kep" / "p103_corpus_audit"
OUT.mkdir(parents=True, exist_ok=True)
RAW  = OUT / "corpus_audit_raw.json"
SMWS_STRIDE = int(os.environ.get("SMWS_STRIDE", "20"))
PAGE_CAP    = int(os.environ.get("PAGE_CAP", "150"))

# ── frozen extractor (import only) ──────────────────────────────────────────
S01 = BASE / "mr-kep" / "book_enrichment_sprint01" / "enrich_mw_yearbook_2019.py"
spec = importlib.util.spec_from_file_location("enrich_s01", str(S01))
s01 = importlib.util.module_from_spec(spec); spec.loader.exec_module(s01)
load_lexicon   = s01.load_production_lexicon
extract_entities = s01.extract_entities

PROD = BASE / "output" / "import" / "production.db"
KDB  = BASE / "mr-kep" / "p102_bootstrap" / "knowledge.db"
lexicon = load_lexicon(str(PROD))
# distillery names for distillery-entity estimate
_p = sqlite3.connect(f"file:{PROD}?mode=ro", uri=True)
UNIVERSE = _p.execute("SELECT COUNT(*) FROM whiskies").fetchone()[0]
DIST_NAMES = {r[0].lower() for r in _p.execute("SELECT DISTINCT name FROM distilleries") if r[0]}
_p.close()

def is_distillery(s):
    s = s.lower().strip()
    return s in DIST_NAMES or any(d in s for d in DIST_NAMES if len(d) > 6)

# current coverage
_k = sqlite3.connect(f"file:{KDB}?mode=ro", uri=True)
COVERED = set(r[0] for r in _k.execute(
    "SELECT DISTINCT cn.whisky_id FROM canonical_vectors cv "
    "JOIN consensus_nodes cn ON cv.consensus_id=cn.consensus_id"))
_k.close()

import fitz
from ebooklib import epub, ITEM_DOCUMENT
from bs4 import BeautifulSoup

def sha256_head(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for _ in range(20):  # first 20 MB for speed
            b = f.read(1 << 20)
            if not b: break
            h.update(b)
    return h.hexdigest()[:16] + "…"

def extract_pdf(path):
    doc = fitz.open(str(path))
    total = len(doc)
    if total <= PAGE_CAP:
        idxs = list(range(total))
    else:
        step = max(1, total // PAGE_CAP)
        idxs = sorted(set([0, total-1] + list(range(0, total, step))))[:PAGE_CAP]
    pages = []
    for i in idxs:
        try: t = doc[i].get_text()
        except Exception: t = ""
        pages.append({"page_num": i+1, "text": t, "text_len": len(t)})
    doc.close()
    return pages, total, len(pages)

def extract_epub(path):
    book = epub.read_epub(str(path))
    docs = []
    for item in book.get_items():
        if item.get_type() == ITEM_DOCUMENT:
            soup = BeautifulSoup(item.get_content(), "html.parser")
            t = soup.get_text("\n")
            if t.strip():
                docs.append({"page_num": len(docs)+1, "text": t, "text_len": len(t)})
    return docs, len(docs)

def estimate(pages):
    res = extract_entities(pages, lexicon)
    resolved = {eid: d for eid, d in res.items() if d.get("whisky_id")}
    unresolved = {eid: d for eid, d in res.items() if not d.get("whisky_id")}
    dist = sum(1 for eid in unresolved if is_distillery(eid))
    wids = {d["whisky_id"] for d in resolved.values()}
    net_new = len(wids - COVERED)
    return {"whisky_ent": len(resolved), "dist_ent": dist, "total_ent": len(res),
            "resolved_wids": sorted(wids), "net_new_wids": net_new}

# signature matching (ingested / registered)
INGESTED_SIG = [
    ("malt whisky yearbook 2019", "ingvar ronde", "9780957655355", "B1"),
    ("world atlas of whisky", "dave broom", "9781845335588", "B2"),
    ("world guide to whisky", "michael jackson", "9780881622843", "B3"),
    ("whisky advocate archive", "whisky advocate", None, "WA_ARCH"),
    ("whisky bible 2020", "jim murray", None, "JMB2020"),
    ("whisky: the manual", "dave broom", None, "DB_MANUAL"),
]
REGISTERED_SIG = [("complete whiskey course", "robin robinson", "9781454932215", "B8")]

def norm(s): return re.sub(r"[^a-z0-9]", " ", (s or "").lower()).strip()
def classify(fn):
    n = norm(fn)
    for t, a, i, sid in INGESTED_SIG:
        if t and t in n: return sid, "INGESTED"
    for t, a, i, sid in REGISTERED_SIG:
        if t and t in n: return sid, "REGISTERED"
    if "whisky advocate" in n or "whisky magazine" in n: return "W3", "UNPROCESSED"
    if "jim murray" in n: return "B4", "UNPROCESSED"
    if "wishart" in n or "flavour of whisky" in n or "whisky classified" in n: return "B5", "UNPROCESSED"
    if "scotch whisky" in n and "annual" in n: return "W3", "UNPROCESSED"
    if "smws" in n.lower(): return "B6", "UNPROCESSED"
    if "complete whiskey course" in n: return "B8", "REGISTERED"
    return "B7", "UNPROCESSED"

EXCLUDE_DIRS = {"acquisition_plan", "output", "__pycache__", ".pytest_cache", "archive"}
EXCLUDE_FILE = re.compile(r"(p2_|review|pack|_ready|_preview|draft|audit|coverage_delta|sprint\d+_report|\.crdownload|enrich_.*\.py|htfw_)")
SCAN = [BASE/"data"/"books", BASE/"data"/"input", BASE/"data"/"manual_sources"]
records = []
SMWS_DIR = BASE/"data"/"books"/"SMWS USA TASTING NOTES ARCHIVE"

def save(): json.dump(records, open(RAW, "w"), indent=2, default=str)

# ── 1) SMWS group (sampled) ─────────────────────────────────────────────────
smws_all = sorted(SMWS_DIR.glob("*")) if SMWS_DIR.exists() else []
smws_sampled = smws_all[::SMWS_STRIDE]
print(f"SMWS group: {len(smws_all)} files, sampling every {SMWS_STRIDE} -> {len(smws_sampled)}")
smws_agg = {"files_in_group": len(smws_all), "sampled": len(smws_sampled),
            "whisky_ent": 0, "dist_ent": 0, "net_new_wids": set()}
for j, p in enumerate(smws_sampled, 1):
    if p.suffix.lower() != ".pdf": continue
    try:
        pages, total, samp = extract_pdf(p)
        est = estimate(pages)
        smws_agg["whisky_ent"] += est["whisky_ent"]
        smws_agg["dist_ent"] += est["dist_ent"]
        smws_agg["net_new_wids"] |= set(est["resolved_wids"])
        records.append({"filename": p.name, "path": str(p.relative_to(BASE)), "format": "pdf",
            "size_bytes": p.stat().st_size, "pages": total, "extractable": True, "sampled": samp < total,
            "entities_est": est["whisky_ent"], "distillery_ent_est": est["dist_ent"],
            "source_id": "B6", "ingest_status": "UNPROCESSED",
            "net_new_wids": len(est["resolved_wids"] - COVERED), "group": "SMWS (sampled)"})
    except Exception as e:
        records.append({"filename": p.name, "path": str(p.relative_to(BASE)), "format": "pdf",
            "size_bytes": p.stat().st_size, "note": f"err {e}", "source_id": "B6", "ingest_status": "UNPROCESSED", "group": "SMWS (sampled)"})
    print(f"  SMWS {j}/{len(smws_sampled)} {p.name[:40]} ent={est['whisky_ent'] if 'est' in dir() else '?'}")
save()

# scale group estimate
scale = len(smws_all) / max(1, len(smws_sampled))
records.append({"filename": f"SMWS USA TASTING NOTES ARCHIVE (GROUP ×{len(smws_all)})",
    "path": "data/books/SMWS USA TASTING NOTES ARCHIVE/", "format": "pdf-group",
    "size_bytes": 0, "pages": len(smws_all), "extractable": True, "sampled": True,
    "entities_est": round(smws_agg["whisky_ent"] * scale), "distillery_ent_est": round(smws_agg["dist_ent"] * scale),
    "source_id": "B6", "ingest_status": "UNPROCESSED",
    "net_new_wids": len(smws_agg["net_new_wids"]), "group": "SMWS (aggregate, scaled)",
    "note": f"sampled {len(smws_sampled)}/{len(smws_all)}, scale×{scale:.1f}"})
save()

# ── 2) all other files ──────────────────────────────────────────────────────
n = 0
for d in SCAN:
    if not d.exists(): continue
    for root, dirs, files in os.walk(d):
        dirs[:] = [x for x in dirs if x not in EXCLUDE_DIRS]
        if SMWS_DIR in [Path(root)] or SMWS_DIR == Path(root):
            continue  # handled above
        for f in files:
            if EXCLUDE_FILE.search(f): continue
            p = Path(root)/f
            ext = p.suffix.lower()
            if ext not in (".pdf",".epub",".csv",".txt",".json",".md"): continue
            n += 1
            try: size = p.stat().st_size
            except Exception: size = 0
            rec = {"filename": f, "path": str(p.relative_to(BASE)), "format": ext[1:],
                   "size_bytes": size, "sha256": sha256_head(p), "pages": None, "chapters": None,
                   "extractable": None, "entities_est": None, "distillery_ent_est": None,
                   "source_id": None, "ingest_status": None, "net_new_wids": None, "note": ""}
            if ext == ".epub":
                try:
                    pages, chap = extract_epub(p); est = estimate(pages)
                    rec.update(chapters=chap, extractable=True, sampled=False,
                        entities_est=est["whisky_ent"], distillery_ent_est=est["dist_ent"],
                        net_new_wids=est["net_new_wids"])
                except Exception as e: rec["note"] = f"epub err: {e}"
            elif ext == ".pdf":
                try:
                    pages, total, samp = extract_pdf(p); est = estimate(pages)
                    rec.update(pages=total, extractable=True, sampled=(samp < total),
                        entities_est=est["whisky_ent"], distillery_ent_est=est["dist_ent"],
                        net_new_wids=est["net_new_wids"])
                except Exception as e: rec["note"] = f"pdf err: {e}"
            elif ext in (".csv",".txt",".json",".md"):
                rec["note"] = "raw data/notes — entity yield by row/structure"
                try:
                    if ext == ".csv":
                        with open(p, encoding="utf-8", errors="ignore") as fh:
                            rec["entities_est"] = max(sum(1 for _ in fh) - 1, 0)
                    elif ext == ".json":
                        rec["entities_est"] = len(json.load(open(p, encoding="utf-8", errors="ignore")))
                except Exception as e: rec["note"] += f" | parse err: {e}"
            sid, status = classify(f)
            rec["source_id"], rec["ingest_status"] = sid, status
            records.append(rec)
            print(f"  [{status:10}] {sid:5} {f[:55]:55} ent={rec.get('entities_est')} pg={rec.get('pages')} ch={rec.get('chapters')} netnew={rec.get('net_new_wids')}")
            if n % 50 == 0: save(); print(f"  -- checkpoint @ {n} files")
    save()
save()

print(f"\nTOTAL records: {len(records)} | UNIVERSE={UNIVERSE} COVERED={len(COVERED)} ({len(COVERED)/UNIVERSE*100:.1f}%)")
print("Wrote", RAW)
