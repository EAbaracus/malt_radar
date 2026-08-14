#!/usr/bin/env python3
"""MR-KEP Book staging contract (P500 book promotion integration).

Defines the canonical book staging representation `staging_book_reviews`
(editorial `staging_editorial_reviews` analogue) and a DETERMINISTIC transform
from P1 `extracted_facts` -> `staging_book_reviews`.

Design rules (per architecture audit + HARD SAFETY):
- `extracted_facts` is the SOURCE OF TRUTH and is NEVER modified/overwritten.
- Transform is deterministic + idempotent (INSERT OR IGNORE on stable evidence_id).
- Entity resolution uses the production lexicon only (no bulk resolution, no
  production write). AMBIGUOUS / NO_MATCH rows are classified, never promoted.
- 7-axis values routed through flavor_scale_utils.to_storage_scale (0-1).
- Writes only to a staging/temp DB passed by the caller (real production/staging
  DBs are never opened RW here).

This module is import-safe and side-effect free until transform() is called.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import sys
from pathlib import Path

# Reuse canonical helpers (no DB access, pure functions)
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT / "mr-kep" / "common") not in sys.path:
    sys.path.insert(0, str(ROOT / "mr-kep" / "common"))
from flavor_scale_utils import to_storage_scale, CANONICAL_AXES  # noqa: E402

CANONICAL_AXES = list(CANONICAL_AXES)

STAGING_BOOK_REVIEWS_SCHEMA = """
CREATE TABLE IF NOT EXISTS staging_book_reviews (
    evidence_id            TEXT PRIMARY KEY,
    matched_master_whisky_id TEXT,
    match_status           TEXT NOT NULL,
    provenance_state       TEXT NOT NULL DEFAULT 'staging_unverified',
    flavor_vector_json     TEXT NOT NULL,
    evidence_confidence    REAL,
    source                 TEXT NOT NULL DEFAULT 'book',
    book_id                TEXT,
    original_fact_id       TEXT,
    entity_key_raw         TEXT,
    er_class               TEXT  -- MATCH / AMBIGUOUS / NO_MATCH (audit classification)
);
"""

# Promotable match statuses (mirrors editorial PROMOTABLE_MATCH)
PROMOTABLE_MATCH = {"exact", "normalized_exact", "fuzzy"}
REJECTED_PROVENANCE = {"staging_rejected", "rejected", "quality_rejected"}


def _norm_name(name: str) -> str:
    """Minimal normalization for entity-key matching (mirrors frozen norm_name)."""
    import re
    n = (name or "").lower().strip()
    n = re.sub(r"[‘’'\"`]", "", n)
    n = re.sub(r"\bthe\b", "", n).strip()
    n = re.sub(r"\s+", " ", n)
    return n


def build_resolution_index(production_db: str):
    """Build (norm_name -> set(whisky_id)) from production.whiskies.

    Returns (name_to_wids, valid_wids). AMBIGUOUS = same norm_name -> >1 wid.
    Read-only against production.db (mode=ro).
    """
    c = sqlite3.connect(f"file:{production_db}?mode=ro", uri=True)
    rows = c.execute("SELECT whisky_id, name FROM whiskies").fetchall()
    c.close()
    name_to_wids = {}
    valid_wids = set()
    for wid, name in rows:
        valid_wids.add(wid)
        key = _norm_name(name)
        if key:
            name_to_wids.setdefault(key, set()).add(wid)
    return name_to_wids, valid_wids


def transform_extracted_to_book_reviews(
    src_db: str,
    dst_db: str,
    book_ids: list[str],
    production_db: str,
    only_p1: bool = True,
) -> dict:
    """Deterministically transform P1 `extracted_facts` into `staging_book_reviews`.

    Reads from src_db (extracted_facts via citation->version->book chain),
    writes to dst_db (staging_book_reviews). src_db is never written.

    Entity resolution: entity_key_raw normalized -> production whisky_id.
      MATCH      : exactly one valid whisky_id
      AMBIGUOUS  : >1 distinct whisky_id for the same name (NOT promotable)
      NO_MATCH   : no whisky_id / not in production.whiskies (NOT promotable)

    Returns a stats dict.
    """
    name_to_wids, valid_wids = build_resolution_index(production_db)

    src = sqlite3.connect(f"file:{src_db}?mode=ro", uri=True)
    src.row_factory = sqlite3.Row
    if only_p1:
        q = (
            "SELECT ef.fact_id, ef.entity_key_raw, ef.descriptor_raw, ef.confidence_score, "
            "ef.status, b.book_id, b.title "
            "FROM extracted_facts ef "
            "JOIN evidence_nodes en ON ef.evidence_id = en.evidence_id "
            "JOIN citations ci ON en.citation_id = ci.citation_id "
            "JOIN book_versions bv ON ci.version_id = bv.version_id "
            "JOIN books b ON bv.book_id = b.book_id "
            "WHERE b.book_id IN (%s)"
            % ",".join("?" for _ in book_ids)
        )
        rows = src.execute(q, book_ids).fetchall()
    else:
        rows = src.execute(
            "SELECT ef.fact_id, ef.entity_key_raw, ef.descriptor_raw, ef.confidence_score, "
            "ef.status, b.book_id, b.title "
            "FROM extracted_facts ef "
            "JOIN evidence_nodes en ON ef.evidence_id = en.evidence_id "
            "JOIN citations ci ON en.citation_id = ci.citation_id "
            "JOIN book_versions bv ON ci.version_id = bv.version_id "
            "JOIN books b ON bv.book_id = b.book_id"
        ).fetchall()
    src.close()

    dst = sqlite3.connect(dst_db)
    dst.execute("PRAGMA foreign_keys=ON")
    dst.executescript(STAGING_BOOK_REVIEWS_SCHEMA)

    stats = {
        "total_input": len(rows),
        "accepted": 0, "rejected": 0,
        "MATCH": 0, "AMBIGUOUS": 0, "NO_MATCH": 0,
        "duplicate": 0, "fk_fail": 0, "malformed": 0,
        "rejected_reasons": {},
    }

    def _rej(reason: str):
        stats["rejected"] += 1
        stats["rejected_reasons"][reason] = stats["rejected_reasons"].get(reason, 0) + 1

    for r in rows:
        fact_id = r["fact_id"]
        entity_key = _norm_name(r["entity_key_raw"] or "")
        # --- Entity resolution ---
        cands = name_to_wids.get(entity_key, set())
        if len(cands) == 0:
            stats["NO_MATCH"] += 1
            _rej("NO_MATCH")
            continue
        if len(cands) > 1:
            stats["AMBIGUOUS"] += 1
            _rej("AMBIGUOUS")
            continue
        wid = next(iter(cands))
        if wid not in valid_wids:
            stats["NO_MATCH"] += 1
            _rej("NO_MATCH_not_in_prod")
            continue
        stats["MATCH"] += 1
        er_class = "MATCH"
        match_status = "exact"

        # --- 7-axis mapping ---
        try:
            desc = json.loads(r["descriptor_raw"]) if r["descriptor_raw"] else {}
        except Exception:
            stats["malformed"] += 1
            _rej("malformed_descriptor_json")
            continue
        vector = {}
        malformed = False
        for ax in CANONICAL_AXES:
            v = desc.get(ax)
            if v is None:
                vector[ax] = 0.0  # canonical convention: missing axis = 0.0
                continue
            sv = to_storage_scale(v)
            if sv is None:
                stats["malformed"] += 1
                _rej("non_numeric_axis")
                malformed = True
                break
            vector[ax] = sv
        if malformed:
            continue

        prov = "staging_unverified"
        try:
            conf = float(r["confidence_score"]) if r["confidence_score"] is not None else 0.0
        except Exception:
            conf = 0.0

        # Deterministic evidence_id (stable across re-runs)
        h = hashlib.sha256(f"{fact_id}|{r['book_id']}".encode()).hexdigest()[:16]
        evidence_id = f"BK-{h}"

        try:
            cur = dst.execute(
                "INSERT OR IGNORE INTO staging_book_reviews "
                "(evidence_id, matched_master_whisky_id, match_status, provenance_state, "
                " flavor_vector_json, evidence_confidence, source, book_id, original_fact_id, "
                " entity_key_raw, er_class) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (evidence_id, wid, match_status, prov,
                 json.dumps(vector), conf, "book", r["book_id"], fact_id,
                 r["entity_key_raw"], er_class),
            )
            if cur.rowcount == 0:
                stats["duplicate"] += 1
            else:
                stats["accepted"] += 1
        except sqlite3.IntegrityError:
            stats["fk_fail"] += 1
            _rej("fk_integrity")

    dst.commit()
    dst.close()
    return stats


if __name__ == "__main__":
    BASE = str(ROOT)
    TEMP = os.environ.get("LOCALAPPDATA", r"C:\Users\eltun\AppData\Local\Temp")
    src = os.path.join(TEMP, "p1_staging_proof.sqlite")
    dst = os.path.join(TEMP, "p1_book_reviews.sqlite")
    if os.path.exists(dst):
        os.remove(dst)
    prod = os.path.join(BASE, "output", "import", "production.db")
    c = sqlite3.connect(f"file:{src}?mode=ro", uri=True)
    p1 = c.execute("SELECT book_id, title FROM books ORDER BY title").fetchall()
    c.close()
    stats = transform_extracted_to_book_reviews(
        src_db=src, dst_db=dst, book_ids=[b[0] for b in p1],
        production_db=prod, only_p1=False,
    )
    print(json.dumps(stats, indent=2))
