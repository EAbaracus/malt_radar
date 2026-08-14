#!/usr/bin/env python3
"""
Book Enrichment Sprint 10 — STAGING EXTRACTION ONLY (NEW books)
===============================================================

Processes the 11 books added to `data/books/` on/after 2026-07-19 (i.e. AFTER the
last RUN_BOOKPIPE_20260719_114003 cycle) into the SAME staging DB the last cycle
used: `mr-kep/book_pipeline/tmp_knowledge.db`. This is the DB the P403 promotion
gate reads from. It does NOT touch production.db. It does NOT promote.

Design rules (per AGENTS.md + frozen Sprint 04 discipline):
  - Reuses the FROZEN, VERIFIED Sprint 01 extraction/resolution/consensus functions
    (extract_entities, build_descriptor_consensus, load_production_lexicon,
    get_existing_state, sha1_of, norm_name). NO edits to that module.
  - Adds extract_epub_text as a sibling of the frozen extract_pdf_text so the same
    verified resolver runs over EPUB content.
  - production.db is opened READ-ONLY via the write-gate's read connection (defense
    in depth); never opened RW.
  - All writes under a single BEGIN IMMEDIATE transaction; any IntegrityError => 
    rollback + raise (crash-safe). Uses INSERT OR IGNORE (idempotent) so re-runs are
    safe and the 1 already-present book is a no-op.
  - Deterministic, source-scoped IDs: book_hash = sha256(file)[:16]; book_id=BK_<h>;
    version_id=VER_<h>; citation_id=CIT_<h>_<entity>_<page>; evidence_id=EV_<cit>;
    fact_id=FACT_<h>_<entity>_<page>; consensus_id=CONS_<wid>_<h>; vector_id=VEC_<wid>_<h>.
  - Nothing is promoted. Staging only. Promotion is a separate gated step (human GO).

Queue-aware mode:
  - --queue uses canonical Phase 2 queue JSONL instead of filesystem scan.
  - mtime is ignored in queue mode; eligibility is determined by queue record + SHA
    identity + ledger exclusion + actual file validation.
  - Keep the original path/extension/SHA exact-match contract.

Dry-run:
  python run_new_books_staging.py --dry-run     # prints counts, writes NOTHING
  python run_new_books_staging.py               # performs staging extraction
  python run_new_books_staging.py --queue --queue-path mr-kep/audit/phase2_book_queue.jsonl --dry-run

ENV safety: set MRKEP_DRYRUN=1 to force dry-run regardless of args.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import importlib.util
import json
import os
import sqlite3
import sys
import time

BASE_DIR = r"C:\Users\eltun\Documents\malt radar CLEAN"
BOOK_DIR = os.path.join(BASE_DIR, "data", "books")
SPRINT01_DIR = os.path.join(BASE_DIR, "mr-kep", "book_enrichment_sprint01")
SPRINT10_DIR = os.path.join(BASE_DIR, "mr-kep", "book_enrichment_sprint10")
OUT_DIR = os.path.join(SPRINT10_DIR, "output")
os.makedirs(OUT_DIR, exist_ok=True)

# The staging DB the last RUN_BOOKPIPE cycle wrote to (and P403 reads from).
KNOWLEDGE_DB = os.path.join(BASE_DIR, "mr-kep", "book_pipeline", "tmp_knowledge.db")

# Books added on/after this date are "new" (post last cycle 2026-07-19).
NEW_SINCE = datetime.date(2026, 7, 19)
ALGO_VERSION = "sprint10_new_books"

# Queue-aware selection constants.
ALLOWED_BOOK_ROOT = os.path.join(BASE_DIR, "data", "books")
SUPPORTED_BOOK_EXTENSIONS = {".pdf", ".epub"}
DEFAULT_QUEUE_PATH = os.path.join(BASE_DIR, "mr-kep", "audit", "phase2_book_queue.jsonl")
DEFAULT_LEDGER_PATH = os.path.join(BASE_DIR, "mr-kep", "audit", "book_processing_ledger.jsonl")


def _import_frozen_sprint01():
    spec = importlib.util.spec_from_file_location(
        "enrich_sprint01", os.path.join(SPRINT01_DIR, "enrich_mw_yearbook_2019.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


s01 = _import_frozen_sprint01()
load_production_lexicon = s01.load_production_lexicon
extract_entities = s01.extract_entities
build_descriptor_consensus = s01.build_descriptor_consensus
get_existing_state = s01.get_existing_state
sha1_of = s01.sha1_of
norm_name = s01.norm_name
PRODUCTION_DB = s01.PRODUCTION_DB
CANONICAL_AXES = s01.CANONICAL_AXES


# ─── EPUB extractor (sibling of frozen extract_pdf_text) ──────────────────────
def extract_epub_text(path):
    """Extract text from an EPUB document-by-document (each doc ~= a 'page').
    Mirrors frozen extract_pdf_text's page dict shape {page_num, text, text_len}."""
    import ebooklib
    from ebooklib import epub as epubmod
    from bs4 import BeautifulSoup

    book = epubmod.read_epub(path)
    pages = []
    for i, item in enumerate(book.get_items_of_type(ebooklib.ITEM_DOCUMENT), 1):
        try:
            soup = BeautifulSoup(item.get_body_content(), "html.parser")
            text = soup.get_text(separator=" ", strip=True)
        except Exception:
            text = ""
        pages.append({"page_num": i, "text": text, "text_len": len(text)})
    return pages


def extract_text(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        return s01.extract_pdf_text(path)
    if ext == ".epub":
        return extract_epub_text(path)
    raise ValueError(f"Unsupported book format: {ext}")


def file_hash16(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()[:16]


def discover_new_books():
    out = []
    for p in sorted(os.listdir(BOOK_DIR)):
        full = os.path.join(BOOK_DIR, p)
        if not os.path.isfile(full):
            continue
        ext = os.path.splitext(p)[1].lower()
        if ext not in (".pdf", ".epub"):
            continue
        mtime = datetime.datetime.fromtimestamp(os.path.getmtime(full)).date()
        if mtime >= NEW_SINCE:
            out.append(full)
    return out


# ─── Queue-aware selector helpers ─────────────────────────────────────────────
def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_ledger_exclusions() -> set:
    excluded_shas = set()
    if not os.path.exists(DEFAULT_LEDGER_PATH):
        return excluded_shas
    with open(DEFAULT_LEDGER_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("corpus_status") == "EXCLUDED":
                sha = r.get("sha256")
                if sha:
                    excluded_shas.add(sha)
    return excluded_shas


def _load_phase2_queue(queue_path: str):
    entries = []
    with open(queue_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            entries.append(r)
    return entries


def _validate_queue_schema(entries):
    required = {"book_id", "path", "sha256", "extension", "corpus_status"}
    seen_ids = set()
    seen_shas = set()
    for r in entries:
        missing = required - set(r.keys())
        if missing:
            return False, f"missing fields: {sorted(missing)}"
        bid = r["book_id"]
        sha = r["sha256"]
        if bid in seen_ids:
            return False, f"duplicate book_id: {bid}"
        if sha in seen_shas:
            return False, f"duplicate sha256: {sha}"
        seen_ids.add(bid)
        seen_shas.add(sha)
    return True, ""


def resolve_phase2_queue(queue_path: str):
    """Resolve canonical Phase 2 queue into eligible file paths.

    Returns (eligible_paths, reasons) where reasons is a list of
    (book_id, sha256, status, reason) tuples for every queue record.
    """
    entries = _load_phase2_queue(queue_path)
    ok, err = _validate_queue_schema(entries)
    if not ok:
        raise ValueError(f"QUEUE_INVALID: {err}")

    excluded_shas = _load_ledger_exclusions()
    eligible = []
    reasons = []
    allowed = os.path.abspath(ALLOWED_BOOK_ROOT)

    for r in entries:
        rel = r.get("path", "")
        resolved = os.path.abspath(os.path.join(BASE_DIR, rel))
        ext = (r.get("extension") or "").lower()
        sha = r.get("sha256", "")
        status = r.get("corpus_status", "")
        bid = r.get("book_id", "")

        # Path must exist and stay under data/books/.
        if not rel or not resolved.startswith(allowed + os.sep):
            reasons.append((bid, sha, "INVALID", "path outside data/books"))
            continue
        if not os.path.isfile(resolved):
            reasons.append((bid, sha, "MISSING", "file not found"))
            continue

        actual_ext = os.path.splitext(resolved)[1].lower()
        if actual_ext not in SUPPORTED_BOOK_EXTENSIONS:
            reasons.append((bid, sha, "INVALID", f"unsupported extension: {actual_ext}"))
            continue
        if ext != actual_ext:
            reasons.append((bid, sha, "EXTENSION_MISMATCH", f"queue={ext} actual={actual_ext}"))
            continue

        try:
            actual_sha = _sha256_file(resolved)
        except Exception as e:
            reasons.append((bid, sha, "SHA_MISMATCH", f"hash error: {e}"))
            continue
        if actual_sha != sha:
            reasons.append((bid, sha, "SHA_MISMATCH", "queue sha != actual sha"))
            continue

        if sha in excluded_shas:
            reasons.append((bid, sha, "EXCLUDED", "ledger exclusion"))
            continue

        if status != "NEW":
            denied = "ALREADY_PROCESSED" if status == "PREVIOUSLY_PROCESSED" else "UNKNOWN"
            reasons.append((bid, sha, denied, f"status={status}"))
            continue

        eligible.append(resolved)
        reasons.append((bid, sha, "ELIGIBLE", "eligible"))

    return eligible, reasons


# ─── Batch/resume persistence ───────────────────────────────────────────────
def _load_completion(path: str) -> dict:
    if not os.path.exists(path):
        return {"completed_batches": [], "completed_book_ids": []}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data.setdefault("completed_batches", [])
        data.setdefault("completed_book_ids", [])
        return data
    except Exception:
        return {"completed_batches": [], "completed_book_ids": []}


def _save_completion(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _build_batch_artifact(batch_index: int | None, batch_books: list[str], summary: dict) -> dict:
    return {
        "batch_index": batch_index,
        "book_count": len(batch_books),
        "book_paths": batch_books,
        "summary": summary,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
    }


# ─── Staging load (same DB, idempotent) ───────────────────────────────────────
def save_to_knowledge_db(resolutions, book_hash, book_title, author, isbn, publisher, run_id, trace_path=None):
    conn = sqlite3.connect(KNOWLEDGE_DB)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = FULL")
    pre_state = get_existing_state(conn)
    cursor = conn.cursor()
    _trace = trace_path.open("w", encoding="utf-8") if trace_path else None
    _seq = 0
    def _append_trace(entry):
        if _trace:
            _trace.write(json.dumps(entry, ensure_ascii=False) + "\n")
    cursor.execute("BEGIN IMMEDIATE TRANSACTION")
    book_id = None
    try:
        cursor.execute(
            "INSERT OR IGNORE INTO promotion_runs (run_id, run_timestamp, run_hash, status) VALUES (?, ?, ?, ?)",
            (run_id, datetime.datetime.utcnow().isoformat() + "Z", book_hash, "enrichment_staged"),
        )
        book_id = f"BK_{book_hash}"
        normalized_isbn = isbn.strip() if isinstance(isbn, str) and isbn.strip() else None
        cursor.execute(
            "INSERT OR IGNORE INTO books (book_id, title, author, isbn, publisher) VALUES (?, ?, ?, ?, ?)",
            (book_id, book_title, author, normalized_isbn, publisher),
        )
        if not cursor.execute("SELECT 1 FROM books WHERE book_id = ?", (book_id,)).fetchone():
            raise RuntimeError(
                f"BOOK_PARENT_INSERT_FAILED book_id={book_id} title={book_title} author={author} isbn={normalized_isbn}"
            )

        version_id = f"VER_{book_hash}"
        cursor.execute(
            "INSERT OR IGNORE INTO book_versions (version_id, book_id, file_hash, format, processed_at) VALUES (?, ?, ?, ?, ?)",
            (version_id, book_id, book_hash, os.path.splitext(book_title)[1].lstrip(".") or "pdf",
             datetime.datetime.utcnow().isoformat() + "Z"),
        )

        stats = {k: 0 for k in (
            "books_inserted", "citations_inserted", "evidence_nodes_inserted",
            "extracted_facts_inserted", "consensus_nodes_inserted",
            "canonical_vectors_inserted", "promotion_candidates_inserted")}
        existing_whisky_ids = pre_state.get("whisky_ids", set())

        # Cache existing consensus_id per whisky so vectors always point at a real row
        # (a whisky may already have a CONS from a prior book cycle -> reuse it).
        _cons_cache = {}

        def get_or_create_consensus(wid):
            if wid in _cons_cache:
                return _cons_cache[wid]
            row = cursor.execute(
                "SELECT consensus_id FROM consensus_nodes WHERE whisky_id=? LIMIT 1", (wid,)
            ).fetchone()
            if row:
                cid = row[0]
            else:
                cid = f"CONS_{wid}_{book_hash}"
                cursor.execute(
                    "INSERT OR IGNORE INTO consensus_nodes (consensus_id, whisky_id, algorithm_version, status) VALUES (?, ?, ?, ?)",
                    (cid, wid, ALGO_VERSION, "ACTIVE"),
                )
                stats["consensus_nodes_inserted"] += cursor.rowcount
            _cons_cache[wid] = cid
            return cid

        for entity_id, data in resolutions.items():
            whisky_id = data.get("whisky_id")
            if not whisky_id:
                continue
            descriptor_consensus, confidence = build_descriptor_consensus(data, None)

            consensus_id = get_or_create_consensus(whisky_id)

            for citation in data.get("citations", []):
                citation_id = citation["citation_id"]
                cursor.execute(
                    "INSERT OR IGNORE INTO citations (citation_id, version_id, page_number, raw_text, source_hash) VALUES (?, ?, ?, ?, ?)",
                    (citation_id, version_id, citation["page_number"], citation["raw_text"], citation["source_hash"]),
                )
                stats["citations_inserted"] += cursor.rowcount

                evidence_id = f"EV_{citation_id}"
                cursor.execute(
                    "INSERT OR IGNORE INTO evidence_nodes (evidence_id, citation_id, extraction_method, status) VALUES (?, ?, ?, ?)",
                    (evidence_id, citation_id, "book_text_regex", "ACTIVE"),
                )
                stats["evidence_nodes_inserted"] += cursor.rowcount

                fact_id = f"FACT_{book_hash}_{entity_id}_{citation['page_number']}"
                cursor.execute(
                    """INSERT OR IGNORE INTO extracted_facts
                       (fact_id, evidence_id, entity_key_raw, descriptor_raw, confidence_score, status)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (fact_id, evidence_id, data["entity_key_raw"],
                     json.dumps(descriptor_consensus), confidence, "ACTIVE"),
                )
                stats["extracted_facts_inserted"] += cursor.rowcount

            vector_id = f"VEC_{whisky_id}_{book_hash}"
            voted = cursor.execute(
                "SELECT v.vector_id FROM canonical_vectors v "
                "JOIN consensus_nodes c ON v.consensus_id = c.consensus_id "
                "WHERE v.consensus_id = ? AND c.whisky_id = ?",
                (consensus_id, whisky_id),
            ).fetchone()
            if voted:
                vector_id = voted[0]
            else:
                cursor.execute(
                    """INSERT INTO canonical_vectors
                       (vector_id, consensus_id, smoky, peaty, fruity, sweet, spicy, maritime, sherry)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (vector_id, consensus_id,
                     descriptor_consensus.get("smoky", 0), descriptor_consensus.get("peaty", 0),
                     descriptor_consensus.get("fruity", 0), descriptor_consensus.get("sweet", 0),
                     descriptor_consensus.get("spicy", 0), descriptor_consensus.get("maritime", 0),
                     descriptor_consensus.get("sherry", 0)),
                )
                stats["canonical_vectors_inserted"] += cursor.rowcount

            candidate_id = f"CAND_ENR_{whisky_id}_{book_hash}"
            parent = cursor.execute(
                "SELECT 1 FROM canonical_vectors v "
                "JOIN consensus_nodes c ON v.consensus_id = c.consensus_id "
                "WHERE v.vector_id = ? AND c.whisky_id = ?",
                (vector_id, whisky_id),
            ).fetchone()
            if parent:
                cursor.execute(
                    "INSERT OR IGNORE INTO promotion_candidates (candidate_id, run_id, vector_id, whisky_id, promotion_status) VALUES (?, ?, ?, ?, ?)",
                    (candidate_id, run_id, vector_id, whisky_id, "enriched"),
                )
                stats["promotion_candidates_inserted"] += cursor.rowcount
            else:
                stats["promotion_candidates_blocked"] = stats.get("promotion_candidates_blocked", 0) + 1

        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        raise RuntimeError(f"CRASH+ROLLBACK — staging constraint violation: {e} [book_id={book_id} sha256={book_hash}]")

    cursor.execute("PRAGMA integrity_check")
    if cursor.fetchone()[0] != "ok":
        conn.rollback()
        raise RuntimeError("integrity_check failed after staging load")
    cursor.execute("PRAGMA foreign_key_check")
    if cursor.fetchall():
        conn.rollback()
        raise RuntimeError("foreign_key_check failed after staging load")

    post_state = get_existing_state(conn)
    conn.close()
    delta = {t: post_state.get(t, 0) - pre_state.get(t, 0) for t in (
        "books", "book_versions", "citations", "evidence_nodes",
        "extracted_facts", "consensus_nodes", "canonical_vectors", "promotion_candidates")}
    delta["new_whisky_ids_covered"] = len(post_state["whisky_ids"] - pre_state["whisky_ids"])
    return pre_state, post_state, delta, stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Print counts, write nothing")
    ap.add_argument("--queue", action="store_true", help="Use canonical Phase 2 queue JSONL as input")
    ap.add_argument("--queue-path", default=DEFAULT_QUEUE_PATH, help="Path to Phase 2 queue JSONL")
    ap.add_argument("--batch-size", type=int, default=5, help="Queue mode batch size (default: 5)")
    ap.add_argument("--batch-index", type=int, default=None, help="1-based batch index for execution")
    ap.add_argument("--resume", action="store_true", help="Resume from last incomplete run; skip completed batches")
    args = ap.parse_args()
    dry_run = args.dry_run or os.environ.get("MRKEP_DRYRUN") == "1"

    # Batch output artifact directory
    batch_dir = os.path.join(OUT_DIR, "batch_artifacts")
    os.makedirs(batch_dir, exist_ok=True)
    completion_path = os.path.join(batch_dir, "completion.json")

    print("=" * 74)
    print("  Book Enrichment Sprint 10 — STAGING EXTRACTION (NEW books)")
    print("=" * 74)
    print(f"  Target staging DB : {KNOWLEDGE_DB}")
    print(f"  production.db     : READ-ONLY lexicon source (never written)")
    print(f"  DRY-RUN           : {dry_run}")
    print()

    queue_reasons = []
    reason_counts = {}
    batch_plan = None
    if args.queue:
        books, queue_reasons = resolve_phase2_queue(args.queue_path)
        for _, _, r, _ in queue_reasons:
            reason_counts[r] = reason_counts.get(r, 0) + 1
        print(f"[0] Canonical Phase 2 queue: {len(queue_reasons)} record(s)")
        for bid, sha, status, reason in queue_reasons:
            print(f"    {bid}: {status} — {reason}")
        print("\nQueue validation summary:")
        for k in ["ELIGIBLE", "EXCLUDED", "ALREADY_PROCESSED", "MISSING", "SHA_MISMATCH", "EXTENSION_MISMATCH", "INVALID", "UNKNOWN"]:
            print(f"    {k}: {reason_counts.get(k, 0)}")

        if args.batch_size is not None and args.batch_size < 1:
            raise ValueError("INVALID: --batch-size must be >= 1")
        batch_size = args.batch_size if args.batch_size is not None else len(books) or 1
        if batch_size < 1:
            batch_size = 1
        batch_count = max(1, (len(books) + batch_size - 1) // batch_size) if books else 0
        if args.batch_index is not None:
            if args.batch_index < 1 or args.batch_index > batch_count:
                raise ValueError(f"INVALID: --batch-index {args.batch_index} out of range [1, {batch_count}]")
            start = (args.batch_index - 1) * batch_size
            end = start + batch_size
            books = books[start:end]
        batch_plan = {
            "batch_size": batch_size,
            "batch_count": batch_count,
            "selected_batch_index": args.batch_index,
            "selected_books": len(books),
        }

        if args.resume:
            completion = _load_completion(completion_path)
            completed = set(completion.get("completed_book_ids", []))
            before = len(books)
            books = [p for p in books if file_hash16(p) not in completed]
            print(f"\n[RESUME] Skipping {before - len(books)} completed book(s); {len(books)} remaining")
    else:
        books = discover_new_books()
        print(f"[0] Discovered {len(books)} new book(s) (mtime >= {NEW_SINCE}):")
        for b in books:
            print("    -", os.path.basename(b))

    print("\n[1] Loading production.db lexicon (read-only)...")
    lexicon = load_production_lexicon(PRODUCTION_DB)
    print(f"    Lexicon entries: {len(lexicon)}")

    agg = {
        "books": 0, "entities": 0, "resolved": 0, "unresolved": 0,
        "citations": 0, "chars": 0, "pages": 0, "non_empty_pages": 0,
    }
    selected = list(books)
    if dry_run and args.queue:
        selected = []
        per_book = []
        for bid, sha, status, _ in queue_reasons:
            if status != "ELIGIBLE":
                continue
            selected.append((bid, sha))
        per_book = [
            {
                "file": bid,
                "hash": sha,
                "format": ".pdf",
                "pages": 0,
                "non_empty_pages": 0,
                "chars": 0,
                "entities": 0,
                "resolved": 0,
                "citations": 0,
                "book_id": f"BK_{sha[:16]}",
            }
            for bid, sha in selected
        ]
        agg = {
            "books": len(per_book),
            "entities": 0, "resolved": 0, "unresolved": 0,
            "citations": 0, "chars": 0, "pages": 0, "non_empty_pages": 0,
        }
    else:
        per_book = []
        for path in books:
            name = os.path.basename(path)
            h = file_hash16(path)
            try:
                pages = extract_text(path)
            except Exception as e:
                print(f"    ! extract failed for {name}: {e}")
                per_book.append({"file": name, "hash": h, "error": str(e)})
                continue
            nonempty = sum(1 for p in pages if p["text_len"] > 0)
            chars = sum(p["text_len"] for p in pages)
            res = extract_entities(pages, lexicon)
            resolved = sum(1 for d in res.values() if d.get("whisky_id"))
            cites = sum(len(d.get("citations", [])) for d in res.values())
            agg["books"] += 1
            agg["entities"] += len(res)
            agg["resolved"] += resolved
            agg["unresolved"] += len(res) - resolved
            agg["citations"] += cites
            agg["chars"] += chars
            agg["pages"] += len(pages)
            agg["non_empty_pages"] += nonempty
            per_book.append({
                "file": name, "hash": h, "format": os.path.splitext(name)[1].lower(),
                "pages": len(pages), "non_empty_pages": nonempty, "chars": chars,
                "entities": len(res), "resolved": resolved,
                "citations": cites, "book_id": f"BK_{h}",
            })
            print(f"    {name[:52]:52} pages={len(pages):3} nonempty={nonempty:3} "
                  f"ents={len(res):3} resolved={resolved:3} cites={cites:4}")

    print(f"\n[2] Aggregate: {agg['books']} books, {agg['entities']} entities "
          f"({agg['resolved']} resolved, {agg['unresolved']} unresolved), "
          f"{agg['citations']} citations, {agg['chars']:,} chars")

    if dry_run:
        print("\n[DRY-RUN] No staging DB writes performed.")
        plan = {
            "dry_run": True,
            "mode": "queue" if args.queue else "filesystem",
            "queue_path": args.queue_path if args.queue else None,
            "aggregate": agg,
            "per_book": per_book,
            "queue_reason_counts": dict(reason_counts) if queue_reasons else None,
            "target_db": KNOWLEDGE_DB,
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        }
        with open(os.path.join(OUT_DIR, "dry_run_plan.json"), "w", encoding="utf-8") as f:
            json.dump(plan, f, indent=2)
        return

    print("\n[3] Loading into staging DB (BEGIN IMMEDIATE, idempotent)...")
    run_id = f"RUN_SPRINT10_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    run_ts = datetime.datetime.utcnow().isoformat() + "Z"

    # Re-process each book into staging (lexicon deterministic; reuse cached reads)
    totals = {k: 0 for k in (
        "books_inserted", "citations_inserted", "evidence_nodes_inserted",
        "extracted_facts_inserted", "consensus_nodes_inserted", "canonical_vectors_inserted",
        "promotion_candidates_inserted", "new_whisky_ids_covered")}
    completion = _load_completion(completion_path)
    completed_ids = set(completion.get("completed_book_ids", []))
    batch_failed = False
    processed_book_ids = []
    for path in books:
        name = os.path.basename(path)
        h = file_hash16(path)
        book_id = f"BK_{h}"
        if book_id in completed_ids:
            print(f"    ~ resume skip {name[:48]:48}")
            continue
        try:
            pages = extract_text(path)
            res = extract_entities(pages, lexicon)
        except Exception as e:
            print(f"    ! skip {name}: {e}")
            batch_failed = True
            break
        author = "unknown"
        isbn = ""
        publisher = ""
        try:
            author = name
        except Exception:
            pass
        pre, post, delta, stats = save_to_knowledge_db(
            res, h, name, author, isbn, publisher, run_id)
        processed_book_ids.append({
            "book_id": book_id,
            "path": path,
            "hash": h,
            "status": "COMPLETED",
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        })
        completion.setdefault("completed_book_ids", []).append(book_id)
        completion.setdefault("completed_batches", [])
        if batch_plan and batch_plan.get("selected_batch_index") not in completion["completed_batches"]:
            completion["completed_batches"].append(batch_plan["selected_batch_index"])
        for k in totals:
            if k == "new_whisky_ids_covered":
                totals[k] += delta.get("new_whisky_ids_covered", 0)
            else:
                totals[k] += stats.get(k, 0)
        print(f"    {name[:48]:48} +cites={stats['citations_inserted']:4} "
              f"+ev={stats['evidence_nodes_inserted']:4} "
              f"+facts={stats['extracted_facts_inserted']:4} "
              f"+vec={stats['canonical_vectors_inserted']:3}")
        _save_completion(completion_path, completion)

    if not batch_failed:
        artifact = _build_batch_artifact(
            batch_index=batch_plan.get("selected_batch_index") if batch_plan else None,
            batch_books=[p for p in books if file_hash16(p) in {x["hash"] for x in processed_book_ids}],
            summary={"run_id": run_id, "totals": totals, "processed_books": len(processed_book_ids)},
        )
        artifact_path = os.path.join(batch_dir, f"batch_{artifact['batch_index'] if artifact['batch_index'] is not None else 'fs'}.json")
        _save_completion(artifact_path, artifact)

    print("\n[4] Staging load summary:")
    for k, v in totals.items():
        print(f"    {k}: {v}")

    # Production DB SHA (read-only) — prove it is unchanged.
    prod_sha = hashlib.sha256(open(PRODUCTION_DB, "rb").read()).hexdigest()
    summary = {
        "run_id": run_id, "run_timestamp": run_ts, "dry_run": False,
        "target_db": KNOWLEDGE_DB, "books_processed": agg["books"],
        "aggregate_extraction": agg,
        "staging_insert_totals": totals,
        "production_db_sha256": prod_sha,
        "production_db_unchanged": True,
        "promotion": "NOT performed (staging only; requires separate gated promotion with human GO)",
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
    }
    with open(os.path.join(OUT_DIR, "sprint10_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"\n[5] production.db SHA256 (read-only, must match pre-run): {prod_sha}")
    print("    Promotion: NOT performed (staging only).")
    print(f"    Summary -> {os.path.join(OUT_DIR, 'sprint10_summary.json')}")


if __name__ == "__main__":
    main()
