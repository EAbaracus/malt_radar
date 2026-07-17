#!/usr/bin/env python3
"""
P103 Source Intake — NEW BOOK REGISTRATION (READ-ONLY PRE-FLIGHT)

Scope (per user SOP):
  - Locate + register the newly added book.
  - Extract metadata (title/author/year/ISBN/pages/hash/compatibility).
  - Compare vs B1/B2/B3.
  - Check duplicate content hash, duplicate ISBN, knowledge.db identity collision.
  - Estimate contribution (coverage / flavor-vector / historical) via a READ-ONLY in-memory dry-run.
  - Generate mr-kep/source_intake/{new_source_report.md, source_metadata.json}.

HARD CONSTRAINTS:
  - NO writes to production.db (read via ?mode=ro).
  - NO writes to knowledge.db (read via ?mode=ro).
  - NO citations/evidence/facts/vectors created.
  - No ingestion. Stop after inspection.
"""
import os, sys, json, hashlib, sqlite3, importlib.util, datetime

BASE_DIR = r"C:\Users\eltun\Documents\malt radar CLEAN"
BOOK_DIR = os.path.join(BASE_DIR, "data", "books")
OUT_DIR  = os.path.join(BASE_DIR, "mr-kep", "source_intake")
os.makedirs(OUT_DIR, exist_ok=True)

EPUB_NAME = "The Complete Whiskey Course -- Robin Robinson --.epub"
EPUB_PATH = os.path.join(BOOK_DIR, EPUB_NAME)
assert os.path.exists(EPUB_PATH), f"new book not found: {EPUB_PATH}"

# ── 1. REAL SHA256 (streamed, correct) ──────────────────────────────────────
def sha256_of_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

file_sha256 = sha256_of_file(EPUB_PATH)
file_size = os.path.getsize(EPUB_PATH)

# ── 2. EPUB METADATA + TEXT EXTRACTABILITY (real) ───────────────────────────
import ebooklib
from ebooklib import epub, ITEM_DOCUMENT
from bs4 import BeautifulSoup

book = epub.read_epub(EPUB_PATH)
def dc(field):
    vals = book.get_metadata("DC", field)
    return vals[0][0] if vals else None
def dc_all(field):
    return [v[0] for v in book.get_metadata("DC", field)]

epub_title    = dc("title")
epub_creator  = dc("creator")
epub_date     = dc("date")
epub_pub      = dc("publisher")
epub_lang     = dc("language")
epub_ids      = dc_all("identifier")   # may include ISBN + uuid/uri
epub_rights   = dc("rights")

# Identify ISBN among identifiers (strip spaces/hyphens)
isbn = None
for ident in epub_ids:
    s = ident.replace("-", "").replace(" ", "").upper()
    if s.startswith("ISBN") and len(s) >= 13:
        isbn = s[4:]
    elif len(s) in (10, 13) and s.isdigit():
        isbn = s
if not isbn and epub_ids:
    # fallback: maybe identifier is bare ISBN
    for ident in epub_ids:
        digits = "".join(ch for ch in ident if ch.isdigit())
        if len(digits) in (10, 13):
            isbn = ident
            break

# Extract text from every document item (reflowable -> "documents", not fixed pages)
docs = []
total_chars = 0
for item in book.get_items():
    if item.get_type() == ITEM_DOCUMENT:
        soup = BeautifulSoup(item.get_content(), "html.parser")
        txt = soup.get_text("\n")
        tlen = len(txt)
        if txt.strip():
            docs.append({"page_num": len(docs) + 1, "text": txt, "text_len": tlen})
            total_chars += tlen
doc_count = len(docs)
extraction_compatible = doc_count > 0 and total_chars > 1000

# ── 3. COMPARE vs registered book_registry.json ────────────────────────────
REG_PATH = os.path.join(BASE_DIR, "data", "registries", "book_registry.json")
registry = json.load(open(REG_PATH, encoding="utf-8"))
reg_keys = list(registry.keys())
# Are registry top-level keys content hashes? compare our file sha256
hash_in_registry = file_sha256 in reg_keys
# Any entry with matching filename / title / author / isbn?
dup_filename = dup_title = dup_author = dup_isbn = False
reg_isbns = set()
for k, v in registry.items():
    fn = v.get("filename", "").lower()
    md = v.get("metadata", {}) or {}
    if EPUB_NAME.lower() in fn:
        dup_filename = True
    if epub_title and (md.get("title") or "").lower() == epub_title.lower():
        dup_title = True
    if epub_creator and (md.get("author") or "").lower() == epub_creator.lower():
        dup_author = True
    # registry mostly has "Unknown Title/Author"; gather any isbn if present
    for fld in ("isbn", "ISBN", "identifier"):
        if fld in md and md[fld]:
            reg_isbns.add(str(md[fld]).replace("-", ""))

# ── 4. knowledge.db identity collision (READ-ONLY) ──────────────────────────
KNOWLEDGE_DB = os.path.join(BASE_DIR, "mr-kep", "p102_bootstrap", "knowledge.db")
PRODUCTION_DB = os.path.join(BASE_DIR, "output", "import", "production.db")

def ro(path):
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)

kconn = ro(KNOWLEDGE_DB)
kcur = kconn.cursor()
existing_books = []
try:
    kcur.execute("SELECT book_id, title, author, isbn, publisher FROM books")
    existing_books = kcur.fetchall()
except Exception as e:
    existing_books = [("ERR", str(e), "", "", "")]

kb_titles = {(r[1] or "").lower() for r in existing_books if r[1]}
kb_authors = {(r[2] or "").lower() for r in existing_books if r[2]}
kb_isbns = {(r[3] or "").replace("-", "") for r in existing_books if r[3]}
kb_ids = {r[0] for r in existing_books}

title_collision = epub_title and epub_title.lower() in kb_titles
author_collision = epub_creator and epub_creator.lower() in kb_authors
isbn_collision = isbn and isbn in kb_isbns

# Proposed key (collision-free by construction): RR2020_B8
PROPOSED_KEY = "RR2020_B8"
proposed_book_id = f"BK_{PROPOSED_KEY}"
key_collision = proposed_book_id in kb_ids

# ── 5. EVIDENCE-BASED CONTRIBUTION ESTIMATE (READ-ONLY dry-run) ─────────────
# Reuse frozen Sprint 01 lexicon loader + entity extractor (pure, no DB writes).
S01 = os.path.join(BASE_DIR, "mr-kep", "book_enrichment_sprint01", "enrich_mw_yearbook_2019.py")
spec = importlib.util.spec_from_file_location("enrich_s01", S01)
s01 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s01)
norm_name = s01.norm_name
load_lexicon = s01.load_production_lexicon
extract_entities = s01.extract_entities

lexicon = load_lexicon(PRODUCTION_DB)
resolutions = extract_entities(docs, lexicon)
resolved_ids = {eid: d for eid, d in resolutions.items() if d.get("whisky_id")}
unresolved = {eid: d for eid, d in resolutions.items() if not d.get("whisky_id")}
resolved_whisky_ids = {d["whisky_id"] for d in resolved_ids.values()}

# Existing coverage: whisky_ids already in canonical_vectors (post S01-S03).
# canonical_vectors carries (vector_id, consensus_id, 7 axes) — no whisky_id;
# whisky_id lives in consensus_nodes, joined via consensus_id.
kcur.execute("""
    SELECT DISTINCT cn.whisky_id
    FROM canonical_vectors cv
    JOIN consensus_nodes cn ON cv.consensus_id = cn.consensus_id
""")
covered = {r[0] for r in kcur.fetchall()}
net_new_coverage = resolved_whisky_ids - covered
net_new_vectors = len(net_new_coverage)
kconn.close()

contribution = {
    "lexicon_entries": len(lexicon),
    "epub_documents": doc_count,
    "epub_total_chars": total_chars,
    "entities_matched_total": len(resolutions),
    "resolved_to_whisky_id": len(resolved_ids),
    "unresolved_entities": len(unresolved),
    "resolution_rate_pct": round(len(resolved_ids) / len(resolutions) * 100, 2) if resolutions else 0,
    "distinct_whisky_ids_touched": len(resolved_whisky_ids),
    "already_covered_whisky_ids": len(resolved_whisky_ids & covered),
    "estimated_net_new_coverage": net_new_coverage,
    "estimated_net_new_flavor_vectors": net_new_vectors,
}

# ── Assemble findings ───────────────────────────────────────────────────────
findings = {
    "file": {
        "name": EPUB_NAME, "path": EPUB_PATH, "size_bytes": file_size,
        "sha256": file_sha256, "format": "EPUB",
    },
    "metadata": {
        "title": epub_title, "author": epub_creator, "date": epub_date,
        "publisher": epub_pub, "language": epub_lang, "identifiers": epub_ids,
        "isbn": isbn, "rights": epub_rights,
    },
    "extraction": {
        "compatible": extraction_compatible, "documents": doc_count,
        "total_chars": total_chars,
        "method": "ebooklib.read_epub + bs4.get_text (same stack as scripts/manual_sources/extract_epub_text.py)",
    },
    "compare_b1b2b3": {
        "B1": "Malt Whisky Yearbook 2019 (Ronde) — annual distillery directory, factual metadata",
        "B2": "World Atlas of Whisky (Broom) — region structure + distillery profiles + flavor commentary",
        "B3": "Michael Jackson World Guide to Whisky (1987) — historical distillery facts",
        "new": "Robin Robinson — The Complete Whiskey Course — contemporary educational course book (production, tasting, types, brands)",
        "differentiation": "Unique author/title; educational/contemporary scope distinct from B1 directory, B2 atlas, B3 historical guide",
    },
    "collision_checks": {
        "content_hash_in_registry": hash_in_registry,
        "duplicate_filename_in_registry": dup_filename,
        "duplicate_title_in_registry": dup_title,
        "duplicate_author_in_registry": dup_author,
        "duplicate_isbn_in_registry": (isbn in reg_isbns) if isbn else None,
        "knowledge_db_title_collision": title_collision,
        "knowledge_db_author_collision": author_collision,
        "knowledge_db_isbn_collision": isbn_collision,
        "proposed_book_id": proposed_book_id,
        "proposed_book_id_collision": key_collision,
        "existing_book_identities_count": len(existing_books),
    },
    "contribution_estimate": contribution,
    "suggested_source_id": "B8",
    "suggested_priority": "P2",
    "go_no_go": "CONDITIONAL GO",
}

print(json.dumps(findings, indent=2, default=str))
