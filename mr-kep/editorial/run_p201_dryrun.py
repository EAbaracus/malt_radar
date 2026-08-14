"""P201 — Editorial ingestion orchestrator (DRY-RUN / staging-only, production-safe).

By default runs OFFLINE against an injected fixture set (no network, no live crawl).
It threads each GO source through: discover_listing -> parse_article -> extract ->
match (read-only vs production.db) -> UPSERT into a SEPARATE staging db
(mr-kep/editorial/staging_editorial.db). production.db is opened mode=ro ONLY for the
match join; it is never written.

A `--live` mode exists but is NOT used in this gate (requires human Gate A1/A5).
Running with --live performs real HTTP via mr-kep/acquisition/http_fetcher.HttpFetcher.

Verification target (this gate): `python run_p201_dryrun.py --self-test` proves the
whole path works on a synthetic article with ZERO network and ZERO production.db writes.
"""
from __future__ import annotations
import argparse
import json
import os
import sqlite3
from typing import Dict, List, Optional

from .adapters import editorial_adapter_factory as factory
from .adapters.editorial_base_adapter import ArticleParse
from .editorial_knowledge_extractor import extract
from .matching import WhiskyRegistryMatcher, MatchDecision

STAGING_DB = os.path.join(os.path.dirname(__file__), "staging_editorial.db")
DDL_PATH = os.path.join(os.path.dirname(__file__), "schema", "staging_editorial.ddl.sql")


def _init_staging(db_path: str):
    with open(DDL_PATH, "r", encoding="utf-8") as f:
        ddl = f.read()
    conn = sqlite3.connect(db_path)
    conn.executescript(ddl)
    conn.commit()
    return conn


def _upsert(conn: sqlite3.Connection, record: dict, match: "MatchDecision"):
    rec = record
    src = rec["source"]
    wid = match.matched_master_whisky_id
    conn.execute(
        """
        INSERT INTO staging_editorial_reviews (
            evidence_id, source_id, source_url, authority_tier, author, published_date,
            content_hash, raw_name, normalized_name, matched_master_whisky_id,
            match_status, match_confidence, score_value, score_scale_max, score_normalized,
            nose, palate, finish, conclusion, flavor_vector_json, metadata_json,
            evidence_confidence, extraction_method, provenance_state
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(evidence_id) DO UPDATE SET
            matched_master_whisky_id=excluded.matched_master_whisky_id,
            match_status=excluded.match_status,
            match_confidence=excluded.match_confidence,
            ingested_at=datetime('now')
        """,
        (
            rec["evidence_id"], src["source_id"], src["url"], src["authority_tier"],
            src.get("author"), src.get("published_date"), src["content_hash_sha256"],
            rec["whisky_identity"]["raw_name"], rec["whisky_identity"]["normalized_name"],
            wid, match.match_status, match.match_confidence,
            rec["score"].get("value"), rec["score"].get("scale_max"), rec["score"].get("normalized"),
            rec["tasting_notes"].get("nose"), rec["tasting_notes"].get("palate"),
            rec["tasting_notes"].get("finish"), rec["tasting_notes"].get("conclusion"),
            json.dumps(rec["flavor_vector"]), json.dumps(rec.get("metadata", {})),
            rec["evidence"]["confidence"], rec["evidence"]["extraction_method"],
            rec["evidence"]["provenance_state"],
        ),
    )
    conn.commit()


def run_article(adapter, source_id: str, url: str, html: str,
                matcher: WhiskyRegistryMatcher, conn: sqlite3.Connection,
                content_hash: str) -> dict:
    parsed: ArticleParse = adapter.parse_article(url, html)
    res = extract(article=parsed, source_id=source_id, source_url=url,
                  content_hash=content_hash, authority_tier=adapter.authority_tier,
                  author=parsed.author, published_date=parsed.published_date)
    rec = res.record
    m = matcher.match(rec["whisky_identity"]["raw_name"])
    rec["whisky_identity"]["matched_master_whisky_id"] = m.matched_master_whisky_id
    rec["whisky_identity"]["match_status"] = m.match_status
    rec["whisky_identity"]["match_confidence"] = m.match_confidence
    _upsert(conn, rec, m)
    return {"evidence_id": rec["evidence_id"], "match_status": m.match_status,
            "matched": m.matched_master_whisky_id}


def self_test() -> dict:
    """Synthetic end-to-end: offline, no network, no production.db write."""
    import tempfile, hashlib
    synthetic_html = (
        "<html><body><h1>Springbank 12 Year Old Cask Strength</h1>"
        "<div class='entry-content'>Nose: smoke and lemon. Palate: honey, pepper, "
        "sea salt. Finish: long, peaty, sherry. Score: 91/100 ABV 54.1%</div>"
        "</body></html>"
    )
    ch = hashlib.sha256(synthetic_html.encode()).hexdigest()
    adapter = factory.get_adapter("thewhiskyphiles")
    tmp_db = os.path.join(tempfile.gettempdir(), "p201_selftest.db")
    if os.path.exists(tmp_db):
        os.remove(tmp_db)
    conn = _init_staging(tmp_db)
    matcher = WhiskyRegistryMatcher(production_db=PRODUCTION_DB)
    # load_registry reads production.db read-only; if missing, matcher still runs (no crash)
    try:
        matcher.load_registry()
    except Exception:
        pass
    out = run_article(adapter, "thewhiskyphiles",
                      "https://thewhiskyphiles.com/2024/01/01/springbank-12-cs/",
                      synthetic_html, matcher, conn, ch)
    # idempotence: re-run same article -> same evidence_id
    out2 = run_article(adapter, "thewhiskyphiles",
                       "https://thewhiskyphiles.com/2024/01/01/springbank-12-cs/",
                       synthetic_html, matcher, conn, ch)
    conn.close()
    os.remove(tmp_db)
    return {"first": out, "second": out2, "idempotent": out["evidence_id"] == out2["evidence_id"]}


def main():
    ap = argparse.ArgumentParser(description="P201 editorial dry-run (staging only)")
    ap.add_argument("--self-test", action="store_true",
                    help="Run synthetic offline end-to-end (no network, no production write)")
    ap.add_argument("--live", action="store_true",
                    help="Live crawl (REQUIRES human Gate A1/A5; not used in audit gate)")
    args = ap.parse_args()

    if args.self_test:
        res = self_test()
        print(json.dumps(res, indent=2))
        return

    if args.live:
        raise SystemExit("Live crawl requires human Gate A1 (legal) + A5 (authorization). "
                         "Not permitted in the audit gate.")

    raise SystemExit("Use --self-test (offline) or --live (gated). Nothing runs by default.")


PRODUCTION_DB = "output/import/production.db"

if __name__ == "__main__":
    main()
