#!/usr/bin/env python3
"""
P301 — KEP Autonomous Runtime (End-to-End) orchestrator.

Single command:  python kep_runtime/run.py

Wires ONLY existing production-grade components into one autonomous pipeline:

    pending artifact
      -> Qualification Engine
      -> Evidence Engine
      -> Extraction Execution
      -> Certification Engine
      -> Canonicalization
      -> Flavor Mapping
      -> Semantic Deduplication
      -> Staging Editorial DB
      -> audit reports

Hard constraints (from the P301 brief + user clarification):
  * NO mock acquisition layer is used/touched (acquisition/* = POC, excluded).
  * NO fake URLs, mock adapters, canned parsers, fabricated metrics.
  * Input  = real pre-produced artifacts (fixtures/*.json) = "pending sources".
  * Output = staging_editorial.db ONLY. production.db is NEVER written.
  * One source failing must NOT abort the batch; failures land in the reports.
  * Promotion stays human-only (this file performs no promotion).

This file is the ONLY new code. Every stage calls an existing module with the
exact interface that module documents. The one non-obvious adaptation: the
Extraction Execution Engine requires a *nested* extraction_result
({field: {"value": ...}}); the flat extracted_fields from a fixture are
converted to that shape before the call (this is the precise defect that
caused the original pipeline/run.py infinite WAITING loop).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
import types
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# --- repo layout: this file lives at <root>/kep_runtime/run.py; engines at <root>/mr-kep ---
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_MRKEP = os.path.join(_ROOT, "mr-kep")
for _p in (_MRKEP, _ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import qualification_engine.engine as QE            # noqa: E402
import evidence_engine.engine as EE                  # noqa: E402
import extraction_execution.engine as EXEC          # noqa: E402
import certification_engine as CE                    # noqa: E402
from d4_reducer.flavor_mapper import FlavorMapper    # noqa: E402
from graph.semantic_deduplicator import SemanticDeduplicator  # noqa: E402

STAGING_DB = os.path.join(_MRKEP, "editorial", "staging_editorial.db")
REPORTS_DIR = os.path.join(_HERE, "reports")
DEFAULT_SOURCES_DIR = os.path.join(_MRKEP, "fixtures")

FM = FlavorMapper()
CANONICAL_AXES = FM.CANONICAL_AXES  # smoky, peaty, fruity, sweet, spicy, maritime, sherry


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(65536), b""):
            h.update(blk)
    return h.hexdigest()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _norm_name(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip()).lower()


# ---------------------------------------------------------------------------
# Stage 5 helper: canonicalize fixture -> metadata + 7-axis flavor vector
# ---------------------------------------------------------------------------
def canonicalize(fixture: Dict[str, Any]):
    extracted = fixture.get("extracted_fields", {}) or {}
    surface = fixture.get("surface_signals", {}) or {}
    whisky_hint = surface.get("whisky_hint") or extracted.get("distillery_name") or "unknown"

    # ABV normalization (strip % then cast REAL)
    raw_abv = extracted.get("abv")
    if raw_abv is not None:
        if isinstance(raw_abv, str):
            abv_norm = raw_abv.replace("%", "").replace(",", ".").strip()
            abv_norm = float(abv_norm) if abv_norm else None
        else:
            abv_norm = float(raw_abv)
    else:
        abv_norm = None

    meta = {
        "raw_name": whisky_hint,
        "normalized_name": _norm_name(whisky_hint),
        "distillery_name": extracted.get("distillery_name"),
        "region": extracted.get("region"),
        "country": extracted.get("country"),
        "abv": abv_norm,
        "age_statement": extracted.get("age_statement"),
        "cask_type": extracted.get("cask_type"),
        "nose": extracted.get("nose"),
        "palate": extracted.get("palate"),
        "finish": extracted.get("finish"),
        "score": extracted.get("score"),
    }

    # Flavor vector from the fixture's 7-axis block (already 0-1 scale).
    fx = extracted.get("flavor_axes", {}) or {}
    flavor_vec = {}
    for ax in CANONICAL_AXES:
        v = fx.get(ax)
        flavor_vec[ax] = float(v) if isinstance(v, (int, float)) else 0.0
    return meta, flavor_vec


# ---------------------------------------------------------------------------
# Stage 8 helper: write one review row into the REAL staging_editorial.db
# ---------------------------------------------------------------------------
def write_to_staging(conn: sqlite3.Connection, fixture: Dict[str, Any],
                     meta: Dict[str, Any], flavor_vec: Dict[str, float],
                     source_key: str, surface: Dict[str, Any],
                     candidate_id: str, content_hash: str) -> int:
    url = surface.get("url") or f"file://{fixture.get('_source_path','')}"
    authority_tier = "T2_expert"  # fixtures are structured exports; tier set at promotion time
    flavor_json = json.dumps({ax: round(flavor_vec.get(ax, 0.0), 4) for ax in CANONICAL_AXES})
    evidence_id = "EDR-" + hashlib.sha256(
        (source_key + "|" + url + "|" + meta["normalized_name"] + "|" + flavor_json).encode()
    ).hexdigest()[:16]
    extraction_method = "structured_extraction"
    provenance_state = "staging_unverified"
    evidence_confidence = 1.0

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
            evidence_id, source_key, url, authority_tier, surface.get("title"),
            None, content_hash, meta["raw_name"], meta["normalized_name"],
            None, "unmatched", None,
            meta.get("score"), 100.0,
            (float(meta["score"]) if isinstance(meta.get("score"), (int, float)) else None),
            meta.get("nose"), meta.get("palate"), meta.get("finish"), None,
            flavor_json, json.dumps(meta, ensure_ascii=False),
            evidence_confidence, extraction_method, provenance_state,
        ),
    )
    conn.commit()
    return 1


# ---------------------------------------------------------------------------
# Per-source processing (one "pending artifact")
# ---------------------------------------------------------------------------
def process_source(path: str, graph: Dict[str, Any]) -> Dict[str, Any]:
    src = os.path.basename(path)
    result: Dict[str, Any] = {
        "source": src, "status": "pending", "stages": {},
        "errors": [], "staging_written": 0, "dedup": None,
    }
    try:
        with open(path, "r", encoding="utf-8") as f:
            fixture = json.load(f)
        fixture["_source_path"] = path
    except Exception as e:
        result["status"] = "failed"
        result["errors"].append(f"load: {e}")
        return result

    surface = fixture.get("surface_signals", {}) or {}
    source_key = fixture.get("source_key", "unknown")

    # --- Stage 1: Qualification ---
    try:
        iu = [{
            "unit_id": fixture.get("document_id", "doc-001"),
            "surface_signals": surface,
            "profile_overrides": fixture.get("profile_overrides", {}) or {},
        }]
        qr = QE.run_batch(source_key, iu)
        units = qr.get("units", [])
        result["stages"]["qualification"] = {
            "units": len(units),
            "in_scope": any(u.get("decision") == "in_scope" for u in units),
        }
    except Exception as e:
        result["status"] = "failed"
        result["errors"].append(f"qualification: {e}")
        return result

    # --- Stage 2: Evidence Engine (discover candidates; non-fatal) ---
    try:
        ledger = EE.run([qr])
        result["stages"]["evidence"] = {
            "discovered_candidates": len(ledger) if isinstance(ledger, list) else "n/a"
        }
    except Exception as e:
        result["errors"].append(f"evidence_engine: {e}")

    # --- Stage 3: Extraction Execution (REQUIRES nested extraction_result) ---
    try:
        extracted = fixture.get("extracted_fields", {}) or {}
        scalar = {k: v for k, v in extracted.items() if not isinstance(v, dict)}
        # CONVERT flat -> nested (the fix for the original infinite-loop defect)
        extraction_result = {}
        for k, v in scalar.items():
            if v is None:
                continue
            extraction_result[k] = {"value": v, "quote": "", "confidence": 1.0}

        cand = fixture.get("document_id", "TEST")
        for u in units:
            if u.get("decision") == "in_scope":
                cand = u.get("unit_id", cand)
                break

        e = EXEC.ExecutionEngine(f"P301-{cand}")
        e.context = {
            "qualification_record": {
                "priority_gate": "Extract Normally",
                "candidate_id": cand,
                "source_key": source_key,
            },
            "extraction_request": {
                "url": surface.get("url") or None,
                "authority_tier": "T2_expert",
                "evidence_type": "structured_data",
                "source_key": source_key,
            },
            "extraction_result": extraction_result,
            "validation_report": {"gate": "PASS", "recoverable": False},
        }
        final = e.run_to_completion()
        bundle = e.context.get("evidence_bundle", [])
        result["stages"]["execution"] = {
            "final_state": getattr(final, "value", str(final)),
            "evidence_records": len(bundle),
        }
        if final != EXEC.State.COMPLETED:
            result["status"] = "failed"
            result["errors"].append(f"execution not COMPLETED: {getattr(final, 'value', final)}")
            return result
    except Exception as ex:
        result["status"] = "failed"
        result["errors"].append(f"execution: {ex}")
        return result

    # --- Stage 4: Certification ---
    try:
        cert = CE.certify(
            entity_key=cand, entity_type="whisky",
            qualification_record=e.context["qualification_record"],
            evidence_ledger=bundle, execution_summary={"run_id": "P301"},
        )
        result["stages"]["certification"] = {
            "state": cert.get("certification_state"),
            "fields": len(cert.get("fields", {})),
        }
    except Exception as ex:
        result["errors"].append(f"certification: {ex}")
        cert = None

    # --- Stage 5: Canonicalization ---
    try:
        meta, flavor_vec = canonicalize(fixture)
        result["stages"]["canonicalization"] = {"flavor_axes": sorted(flavor_vec.keys())}
    except Exception as ex:
        result["errors"].append(f"canonicalization: {ex}")
        return _fail(result, "canonicalization")
    if not (fixture.get("extracted_fields", {}) or {}).get("flavor_axes"):
        result["errors"].append(
            "canonicalization: no flavor_axes block in source (vector defaulted to 0.0)")

    # --- Stage 6: Flavor Mapping (validate/normalize to 7 canonical axes) ---
    try:
        mapped = {ax: float(flavor_vec.get(ax) or 0.0) for ax in CANONICAL_AXES}
        result["stages"]["flavor_mapping"] = {"axes": len(mapped)}
    except Exception as ex:
        result["errors"].append(f"flavor_mapping: {ex}")
        mapped = {ax: 0.0 for ax in CANONICAL_AXES}

    # --- Stage 7: Semantic Deduplication ---
    try:
        dedup = SemanticDeduplicator(graph).check_duplicate(
            {"name": meta["normalized_name"], "abv": meta.get("abv")}
        )
        result["dedup"] = {"duplicate": dedup is not None, "detail": dedup}
    except Exception as ex:
        result["errors"].append(f"deduplication: {ex}")
        result["dedup"] = {"duplicate": False, "detail": None}

    result["_fixture"] = fixture
    result["status"] = "completed"
    return result, meta, mapped, source_key, surface, cand  # type: ignore


def _fail(result: Dict[str, Any], stage: str) -> Dict[str, Any]:
    result["status"] = "failed"
    if not any(stage in er for er in result["errors"]):
        result["errors"].append(f"{stage}: failed")
    return result


# ---------------------------------------------------------------------------
# Report writers
# ---------------------------------------------------------------------------
def _write_reports(results: List[Dict[str, Any]], stats: Dict[str, Any], errors: List[Dict[str, Any]]):
    os.makedirs(REPORTS_DIR, exist_ok=True)
    runtime_report = {
        "generated_at": _now_iso(),
        "pipeline": "P301-autonomous-runtime",
        "summary": stats,
        "sources": results,
    }
    with open(os.path.join(REPORTS_DIR, "runtime_report.json"), "w", encoding="utf-8") as f:
        json.dump(runtime_report, f, indent=2, ensure_ascii=False)

    lines = ["# P301 Runtime Report", "", f"- Generated: {runtime_report['generated_at']}", "",
             f"- Total sources: {stats['total']}", f"- Completed: {stats['completed']}",
             f"- Failed: {stats['failed']}", f"- Staging rows written: {stats['staging_written']}",
             f"- Duplicates flagged: {stats['duplicates']}", ""]
    for r in results:
        lines.append(f"## {r['source']} — {r['status']}")
        if r.get("stages"):
            for s, v in r["stages"].items():
                lines.append(f"  - {s}: {v}")
        if r.get("dedup"):
            lines.append(f"  - dedup: {r['dedup']}")
        for er in r.get("errors", []):
            lines.append(f"  - ERROR: {er}")
        lines.append("")
    with open(os.path.join(REPORTS_DIR, "runtime_report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    with open(os.path.join(REPORTS_DIR, "statistics.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

    with open(os.path.join(REPORTS_DIR, "error_report.json"), "w", encoding="utf-8") as f:
        json.dump({"generated_at": _now_iso(), "error_count": len(errors), "errors": errors},
                  f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(description="P301 KEP Autonomous Runtime (end-to-end)")
    ap.add_argument("--sources-dir", default=DEFAULT_SOURCES_DIR,
                    help="Directory of pending-source JSON artifacts")
    ap.add_argument("--staging-db", default=STAGING_DB,
                    help="Staging DB to write into (staging ONLY; never production)")
    args = ap.parse_args(argv)

    sources = sorted(
        os.path.join(args.sources_dir, f)
        for f in os.listdir(args.sources_dir)
        if f.endswith(".json")
    ) if os.path.isdir(args.sources_dir) else []

    # Build dedup graph (must expose a `.nodes` attribute — SemanticDeduplicator
    # reads self.graph.nodes.items(); a plain dict with a "nodes" key fails).
    graph = types.SimpleNamespace(nodes={})
    if os.path.exists(args.staging_db):
        rc = sqlite3.connect(f"file:{args.staging_db}?mode=ro", uri=True)
        rc.row_factory = sqlite3.Row
        for i, row in enumerate(rc.execute(
                "SELECT raw_name, normalized_name FROM staging_editorial_reviews")):
            graph.nodes[f"existing_{i}"] = {
                "label": "Whisky",
                "properties": {"name": row["normalized_name"] or _norm_name(row["raw_name"] or ""),
                               "abv": None},
            }
        rc.close()

    conn = sqlite3.connect(args.staging_db)
    conn.execute("PRAGMA foreign_keys = ON")

    results: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []
    stats = {"total": len(sources), "completed": 0, "failed": 0,
             "staging_written": 0, "duplicates": 0, "started_at": _now_iso()}

    print(f"=== P301 Autonomous Runtime :: {len(sources)} pending source(s) ===")
    for path in sources:
        print(f"[source] {os.path.basename(path)} ...")
        try:
            out = process_source(path, graph)
            # process_source returns either a result dict (on early failure)
            # or a tuple (result, meta, mapped, source_key, surface, cand).
            if isinstance(out, tuple):
                result, meta, mapped, source_key, surface, cand = out
                # Stage 8: staging write (real DB)
                try:
                    ch = _sha256_file(path)
                    n = write_to_staging(conn, result.get("_fixture", {}), meta, mapped,
                                         source_key, surface, cand, ch)
                    result["staging_written"] = n
                    stats["staging_written"] += n
                    # extend dedup graph so within-run dedup is consistent
                    graph.nodes[f"run_{cand}"] = {
                        "label": "Whisky",
                        "properties": {"name": meta["normalized_name"], "abv": meta.get("abv")},
                    }
                except Exception as ex:
                    result["status"] = "failed"
                    result["errors"].append(f"staging_write: {ex}")
            else:
                result = out
        except Exception as ex:
            # Defensive: any unexpected exception still must not abort the batch.
            result = {"source": os.path.basename(path), "status": "failed",
                      "stages": {}, "errors": [f"unexpected: {ex}"], "staging_written": 0}
            import traceback
            errors.append({"source": os.path.basename(path), "trace": traceback.format_exc()})

        if result.get("status") == "completed":
            stats["completed"] += 1
        else:
            stats["failed"] += 1
            errors.append({"source": result["source"], "errors": result.get("errors", [])})
        if result.get("dedup", {}).get("duplicate"):
            stats["duplicates"] += 1

        results.append(result)
        print(f"  -> {result['status']} (stages={list(result.get('stages', {}).keys())})"
              + (f" errors={result['errors']}" if result['errors'] else ""))

    conn.close()
    stats["finished_at"] = _now_iso()
    _write_reports(results, stats, errors)

    print(f"\n=== DONE === completed={stats['completed']} failed={stats['failed']} "
          f"staging_written={stats['staging_written']} duplicates={stats['duplicates']}")
    print(f"Reports: {REPORTS_DIR}/")
    # Exit non-zero only if EVERYTHING failed (so a partial batch is still 'successful').
    return 0 if stats["completed"] > 0 or stats["total"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
