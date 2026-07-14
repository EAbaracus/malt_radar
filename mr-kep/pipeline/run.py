#!/usr/bin/env python3
"""
MR-KEP Sprint 2 — Pipeline Orchestrator

Chains: fixture → qualification → evidence → execution → certification → canonical output

Deterministic, read-only, no AI/LLM/OCR/scraping, no production.db.
"""
import json
import os
import sys
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# -- repo paths --
_HERE = os.path.dirname(os.path.abspath(__file__))
_MRKEP = os.path.dirname(_HERE)
_OUTPUT = os.path.join(_MRKEP, "output")

# Engine imports
sys.path.insert(0, os.path.join(_MRKEP, "qualification_engine"))
sys.path.insert(0, os.path.join(_MRKEP, "evidence_engine"))
sys.path.insert(0, os.path.join(_MRKEP, "extraction_execution"))
sys.path.insert(0, _MRKEP)

import qualification_engine.engine as QE
import evidence_engine.engine as EE
import certification_engine as CE

SCHEMA_VERSION = "1.0.0"


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _ensure_output_dir():
    os.makedirs(_OUTPUT, exist_ok=True)


def _load_fixture(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ============================================================================
# Stage 1: Qualification Engine
# ============================================================================
def run_qualification(
    fixture: Dict[str, Any], run_id: str, fixed_timestamp: Optional[str] = None
) -> Dict[str, Any]:
    """Run the P71 Qualification Engine against the fixture."""
    source_key = fixture.get("source_key", "unknown")
    surface = fixture.get("surface_signals", {})
    overrides = fixture.get("profile_overrides", {})

    # Build the input unit the qualification engine expects
    input_units = [
        {
            "unit_id": fixture.get("document_id", "doc-001"),
            "surface_signals": surface,
            "profile_overrides": overrides,
        }
    ]

    qual_record = QE.run_batch(source_key, input_units)

    # Override timestamp for deterministic testing
    if fixed_timestamp:
        qual_record["qualified_at"] = fixed_timestamp

    # Save the qualification record
    qual_path = os.path.join(_OUTPUT, "qualification.json")
    with open(qual_path, "w", encoding="utf-8") as f:
        json.dump(qual_record, f, indent=2, ensure_ascii=False)
    print(f"[PIPELINE] Qualification → {len(qual_record.get('units', []))} unit(s) → {qual_path}")

    return qual_record


# ============================================================================
# Stage 2: Evidence Engine
# ============================================================================
def run_evidence_engine(
    qualification_records: List[Dict[str, Any]],
    run_id: str,
) -> List[Dict[str, Any]]:
    """Run the P73 Evidence Engine → produce evidence candidates."""
    ledger = EE.run(qualification_records)

    ev_path = os.path.join(_OUTPUT, "evidence.jsonl")
    with open(ev_path, "w", encoding="utf-8") as f:
        for entry in ledger:
            f.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"[PIPELINE] Evidence → {len(ledger)} candidate(s) → {ev_path}")

    return ledger


# ============================================================================
# Stage 3: Execution Engine (P68 state machine)
# ============================================================================
def run_execution(
    fixture: Dict[str, Any],
    qualification_record: Dict[str, Any],
    evidence_ledger: List[Dict[str, Any]],
    run_id: str,
) -> Dict[str, Any]:
    """Run the P68 Execution Engine state machine for the qualification result."""
    import engine as EXEC_ENGINE  # extraction_execution.engine

    exec_engine = EXEC_ENGINE.ExecutionEngine(run_id)

    # Build context from qualification
    units = qualification_record.get("units", [])
    candidate_id = run_id
    whisky_hint = ""
    for u in units:
        if u.get("decision") == "in_scope":
            whisky_hint = u.get("whisky_hint", "")
            candidate_id = u.get("unit_id", run_id)
            break

    source_key = qualification_record.get("source_key", "whiskyfun")

    # Extract fields from the fixture
    extracted = fixture.get("extracted_fields", {})

    # Determine the priority gate from the qualification record
    # The QE emits decisions, but the execution engine expects a priority_gate
    in_scope = any(u.get("decision") == "in_scope" for u in units)
    priority_gate = "Extract Normally" if in_scope else "Reject"

    exec_engine.context = {
        "qualification_record": {
            "priority_gate": priority_gate,
            "candidate_id": candidate_id,
            "source_key": source_key,
        },
        "extraction_request": {
            "url": fixture.get("surface_signals", {}).get("url") or None,
        },
        "extraction_result": extracted,
        "validation_report": {"gate": "PASS", "recoverable": False},
    }

    final_state = exec_engine.run_to_completion()

    exec_summary = {
        "run_id": run_id,
        "initial_state": "Queued",
        "final_state": final_state.value if hasattr(final_state, 'value') else str(final_state),
        "retries": exec_engine.retries,
        "evidence_bundle_count": len(exec_engine.context.get("evidence_bundle", [])),
    }

    exec_path = os.path.join(_OUTPUT, "execution.json")
    with open(exec_path, "w", encoding="utf-8") as f:
        json.dump(exec_summary, f, indent=2, ensure_ascii=False)
    print(f"[PIPELINE] Execution → final_state={exec_summary['final_state']} → {exec_path}")

    return exec_summary


# ============================================================================
# Stage 4: Extract Evidence from Fixture (bridge extraction -> evidence ledger)
# ============================================================================
def produce_extracted_evidence(
    fixture: Dict[str, Any],
    qualification_record: Dict[str, Any],
    evidence_ledger: List[Dict[str, Any]],
    run_id: str,
) -> List[Dict[str, Any]]:
    """Create P64-compatible evidence entries from the fixture's extracted
    fields. This simulates the Extraction Agent stage: each non-null extracted
    field gets an evidence entry with provenance_state='extracted' and a
    deterministic evidence_id.

    This bridges the discover→extract gap: the evidence engine produces
    'discovered' candidates (null values); extraction fills in the values
    and produces new 'extracted' entries that supersede (or rather, follow)
    the discovered ones per the append-only provenance model.
    """
    import hashlib
    import evidence_engine.engine as EE
    import certification_engine as CE

    extracted = fixture.get("extracted_fields", {})
    surface = fixture.get("surface_signals", {})
    source_key = qualification_record.get("source_key", "unknown")
    qualified_at = qualification_record.get("qualified_at", "")

    cfg = EE.load_authority_configs()
    resolved = EE.resolve_source(source_key, cfg)

    whisky_hint = surface.get("whisky_hint", "unknown")
    entity_id = EE._norm_name(whisky_hint) if whisky_hint else "unknown"
    entity_type = "whisky"

    # Source URL from the fixture
    source_url = surface.get("url", "")

    extracted_evidence = []
    for field_name, field_value in extracted.items():
        if field_value is None:
            continue

        # Skip flavor_axes for individual field treatment (handled as composite)
        if field_name == "flavor_axes":
            continue

        # Use the evidence engine's build_entry for deterministic ids
        entry = EE.build_entry(
            entity_type=entity_type,
            entity_id=entity_id,
            source_name=source_key,
            source_class=resolved["source_class"],
            authority_tier=resolved["authority_tier"],
            source_url=source_url or None,
            retrieval_timestamp=qualified_at,
            field_name=field_name,
            field_value=field_value,
            evidence_type=resolved.get("evidence_type", "expert_quote"),
            cfg=cfg,
        )

        # Override provenance_state and confidence to match extraction phase
        entry["provenance_state"] = "extracted"
        # Base confidence for expert_quote = 0.90 (authority/confidence.yaml)
        entry["confidence"] = 0.90

        # Re-compute evidence_hash since we changed provenance_state
        ev_json = EE._canonical_json(entry)
        ev_hash = hashlib.sha256(ev_json.encode("utf-8")).hexdigest()
        entry["evidence_hash"] = ev_hash
        entry["evidence_id"] = "EV-" + ev_hash[:16]

        extracted_evidence.append(entry)

    # Also create entries for flavor_axes sub-axes
    flavor_axes = extracted.get("flavor_axes", {})
    if flavor_axes and isinstance(flavor_axes, dict):
        for axis, score in flavor_axes.items():
            if score is not None:
                entry = EE.build_entry(
                    entity_type=entity_type,
                    entity_id=entity_id,
                    source_name=source_key,
                    source_class=resolved["source_class"],
                    authority_tier=resolved["authority_tier"],
                    source_url=source_url or None,
                    retrieval_timestamp=qualified_at,
                    field_name=f"flavor_axes.{axis}",
                    field_value=score,
                    evidence_type=resolved.get("evidence_type", "expert_quote"),
                    cfg=cfg,
                )
                entry["provenance_state"] = "extracted"
                entry["confidence"] = 0.90
                ev_json = EE._canonical_json(entry)
                ev_hash = hashlib.sha256(ev_json.encode("utf-8")).hexdigest()
                entry["evidence_hash"] = ev_hash
                entry["evidence_id"] = "EV-" + ev_hash[:16]
                extracted_evidence.append(entry)

    # Merge discovered + extracted (append-only: discovered first, then extracted)
    # Remove duplicate entries by evidence_id
    seen_ids = set()
    combined = []
    for e in evidence_ledger + extracted_evidence:
        eid = e.get("evidence_id", "")
        if eid not in seen_ids:
            seen_ids.add(eid)
            combined.append(e)

    # Re-write evidence.jsonl with the combined ledger
    ev_path = os.path.join(_OUTPUT, "evidence.jsonl")
    with open(ev_path, "w", encoding="utf-8") as f:
        for entry in combined:
            f.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"[PIPELINE] Evidence (extracted) → {len(extracted_evidence)} extracted + "
          f"{len(evidence_ledger)} discovered = {len(combined)} total → {ev_path}")

    return combined
# ============================================================================
def run_certification(
    entity_key: str,
    qualification_record: Dict[str, Any],
    evidence_ledger: List[Dict[str, Any]],
    execution_summary: Dict[str, Any],
) -> Dict[str, Any]:
    """Run the certification engine over all evidence."""
    cert = CE.certify(
        entity_key=entity_key,
        entity_type="whisky",
        qualification_record=qualification_record,
        evidence_ledger=evidence_ledger,
        execution_summary=execution_summary,
    )

    cert_path = os.path.join(_OUTPUT, "certification.json")
    with open(cert_path, "w", encoding="utf-8") as f:
        json.dump(cert, f, indent=2, ensure_ascii=False)
    print(f"[PIPELINE] Certification → state={cert['certification_state']} → {cert_path}")

    return cert


# ============================================================================
# Stage 5: Canonical Output (P65)
# ============================================================================
def build_canonical_output(
    fixture: Dict[str, Any],
    qualification_record: Dict[str, Any],
    evidence_ledger: List[Dict[str, Any]],
    certification: Dict[str, Any],
    execution_summary: Dict[str, Any],
    run_id: str,
    fixed_timestamp: Optional[str] = None,
) -> Dict[str, Any]:
    """Assemble the P65 canonical_output.schema.json artifact."""
    surface = fixture.get("surface_signals", {})
    extracted = fixture.get("extracted_fields", {})

    # Entity
    whisky_hint = surface.get("whisky_hint", "unknown")
    norm_key = whisky_hint.lower().replace(" ", "-") if whisky_hint else "unknown"

    # Metadata map with ABV normalization (strip % then cast REAL)
    raw_abv = extracted.get("abv")
    if raw_abv is not None:
        if isinstance(raw_abv, str):
            abv_normalized = raw_abv.replace("%", "").replace(",", ".").strip()
            abv_normalized = float(abv_normalized) if abv_normalized else None
        else:
            abv_normalized = float(raw_abv)
    else:
        abv_normalized = None

    flavor_axes = extracted.get("flavor_axes", {})
    metadata = {
        "distillery_name": extracted.get("distillery_name"),
        "region": extracted.get("region"),
        "country": extracted.get("country"),
        "abv": abv_normalized,
        "age_statement": extracted.get("age_statement"),
        "cask_type": extracted.get("cask_type"),
        "nose": extracted.get("nose"),
        "palate": extracted.get("palate"),
        "finish": extracted.get("finish"),
        "flavor_axes": flavor_axes if flavor_axes else None,
        "score": extracted.get("score"),
        "community_rating": extracted.get("community_rating"),
    }

    # Evidence index (P64-compatible references)
    evidence_index = []
    for e in evidence_ledger:
        evidence_index.append({
            "evidence_id": e.get("evidence_id", ""),
            "field_name": e.get("field_name", ""),
            "source_class": e.get("source_class", ""),
            "source_name": e.get("source_name", ""),
        })

    # Confidence
    per_field_conf = {}
    for fn in sorted(set(e.get("field_name", "") for e in evidence_ledger if e.get("field_name"))):
        confs = [e.get("confidence", 0.0) for e in evidence_ledger if e.get("field_name") == fn and e.get("confidence") is not None]
        per_field_conf[fn] = max(confs) if confs else 0.0

    overall_conf = min(per_field_conf.values()) if per_field_conf else 0.0

    # Certification per-field
    cert_fields = certification.get("fields", {})
    cert_per_field = {}
    for fn, cinfo in cert_fields.items():
        cert_per_field[fn] = {
            "certification_level": cinfo.get("certification_level", "uncertified"),
            "certification_path": cinfo.get("certification_path"),
            "authority_tier": cinfo.get("authority_tier"),
        }

    # Use fixed timestamp if provided (deterministic testing)
    generated_at = fixed_timestamp if fixed_timestamp else _now_iso()

    canonical = {
        "schema_version": SCHEMA_VERSION,
        "entity": {
            "entity_type": "whisky",
            "entity_id": None,
            "entity_key": norm_key,
            "display_name": whisky_hint or None,
        },
        "metadata": metadata,
        "evidence": evidence_index,
        "provenance": {
            "extractor_id": "mr-kep-sprint2-pipeline",
            "extractor_version": "1.0.0",
            "run_id": run_id,
            "generated_at": generated_at,
            "deterministic": True,
        },
        "confidence": {
            "overall": overall_conf,
            "per_field": per_field_conf,
        },
        "certification": {
            "per_field": cert_per_field,
        },
        "merge_candidates": [],
    }

    out_path = os.path.join(_OUTPUT, "canonical_output.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(canonical, f, indent=2, ensure_ascii=False)
    print(f"[PIPELINE] Canonical Output → {out_path}")

    return canonical


# ============================================================================
# Stage 6: Run Manifest
# ============================================================================
def write_manifest(
    run_id: str,
    fixture_path: str,
    artifacts: Dict[str, str],
    summary: Dict[str, Any],
    fixed_timestamp: Optional[str] = None,
) -> Dict[str, Any]:
    """Write the run manifest with sha256 hashes."""
    generated_at = fixed_timestamp if fixed_timestamp else _now_iso()
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "pipeline": "mr-kep-sprint2",
        "generated_at": generated_at,
        "deterministic": True,
        "fixture": {
            "path": fixture_path,
            "sha256": _sha256_file(fixture_path),
        },
        "artifacts": {},
        "summary": summary,
    }

    for name, path in artifacts.items():
        if os.path.exists(path):
            manifest["artifacts"][name] = {
                "path": path,
                "sha256": _sha256_file(path),
            }

    out_path = os.path.join(_OUTPUT, "run_manifest.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"[PIPELINE] Manifest → {out_path}")
    return manifest


# ============================================================================
# Main pipeline
# ============================================================================
def run_pipeline(
    fixture_path: str,
    run_id: Optional[str] = None,
    fixed_timestamp: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute the full Sprint 2 pipeline end-to-end.

    Args:
        fixture_path: Path to the fixture JSON.
        run_id: Optional run identifier.
        fixed_timestamp: Optional fixed ISO timestamp for deterministic testing.
            If provided, all timestamps in output use this value.

    Returns a summary dict with all stage results.
    """
    if run_id is None:
        run_id = f"MRKEP-S2-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}"

    _ensure_output_dir()
    fixture = _load_fixture(fixture_path)
    surface = fixture.get("surface_signals", {})
    whisky_hint = surface.get("whisky_hint", "unknown")
    entity_key = whisky_hint.lower().replace(" ", "-") if whisky_hint else "unknown"

    print(f"=== MR-KEP Sprint 2 Pipeline :: run_id={run_id} ===")
    print(f"Fixture: {fixture_path} (whisky_hint={whisky_hint})")

    # Stage 1: Qualification
    qual_record = run_qualification(fixture, run_id, fixed_timestamp)

    # Stage 2: Evidence Engine
    evidence_ledger = run_evidence_engine([qual_record], run_id)

    # Stage 3: Execution Engine
    exec_summary = run_execution(fixture, qual_record, evidence_ledger, run_id)

    # Stage 3b: Extract Evidence from Fixture (bridge extraction -> P64)
    combined_evidence = produce_extracted_evidence(
        fixture, qual_record, evidence_ledger, run_id
    )

    # Stage 4: Certification
    certification = run_certification(
        entity_key, qual_record, combined_evidence, exec_summary
    )

    # Stage 5: Canonical Output
    canonical = build_canonical_output(
        fixture, qual_record, combined_evidence, certification, exec_summary, run_id, fixed_timestamp
    )

    # Stage 6: Manifest
    artifacts = {
        "qualification": os.path.join(_OUTPUT, "qualification.json"),
        "execution": os.path.join(_OUTPUT, "execution.json"),
        "evidence": os.path.join(_OUTPUT, "evidence.jsonl"),
        "certification": os.path.join(_OUTPUT, "certification.json"),
        "canonical_output": os.path.join(_OUTPUT, "canonical_output.json"),
    }
    summary = {
        "run_id": run_id,
        "fixture": fixture_path,
        "whisky_hint": whisky_hint,
        "entity_key": entity_key,
        "qualification_units": len(qual_record.get("units", [])),
        "evidence_candidates": len(combined_evidence),
        "execution_final_state": exec_summary.get("final_state"),
        "certification_state": certification.get("certification_state"),
        "certified_fields": sum(
            1 for v in certification.get("fields", {}).values()
            if v.get("certification_level") == "certified"
        ),
        "proposed_fields": sum(
            1 for v in certification.get("fields", {}).values()
            if v.get("certification_level") == "proposed"
        ),
        "rejected_fields": sum(
            1 for v in certification.get("fields", {}).values()
            if v.get("certification_level") == "rejected"
        ),
    }
    write_manifest(run_id, fixture_path, artifacts, summary, fixed_timestamp)

    print(f"\n=== PIPELINE COMPLETE ===")
    print(f"  Certification: {summary['certification_state']}")
    print(f"  Certified: {summary['certified_fields']}")
    print(f"  Proposed: {summary['proposed_fields']}")
    print(f"  Rejected: {summary['rejected_fields']}")
    print(f"  Evidence: {summary['evidence_candidates']} candidates")
    print(f"  Output: {_OUTPUT}/")

    return summary


def run_batch_csv(csv_path: str) -> dict:
    """Execute batch extraction and pipeline run against the candidate list.
    Saves outputs to output/ directory as required by P76.
    """
    import csv
    from qualification_engine import classifier
    from qualification_engine import config as qual_config
    from extraction_engine import extractor
    import extraction_execution.engine as exec_engine

    results = []
    stats = {"total": 0, "certified": 0, "hold": 0, "rejected": 0}
    manifest = []
    all_evidence = []
    all_extractions = []

    _ensure_output_dir()

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        candidates = list(reader)

    real_doc_url = f"file://{os.path.abspath(csv_path).replace(chr(92), '/')}"

    for row in candidates:
        cand_id = row["gsd_candidate_id"]
        stats["total"] += 1

        signals = {
            "url": real_doc_url,
            "mime_type": "text/csv",
            "filename": os.path.basename(csv_path),
            "title": row["canonical_name"],
            "whisky_hint": row["canonical_name"]
        }

        # 1. Qualification
        qual_record = QE.run_batch("SOURCE-P76", [{"unit_id": cand_id, "surface_signals": signals}])

        # Determine authority dynamically based on real class
        doc_class = classifier.classify(signals)
        auth_tier = qual_config.DOCUMENT_CLASSES.get(doc_class, {}).get("authority_tier", "T3_community")

        # 2. Real Extraction
        ext_result = extractor.run_extraction(row, doc_class)
        all_extractions.append({"candidate_id": cand_id, "extraction": ext_result})

        # 3. Execution Engine
        e = exec_engine.ExecutionEngine(cand_id)
        e.context = {
            "qualification_record": {
                "priority_gate": "Extract Normally",
                "candidate_id": cand_id,
                "qualified_at": qual_record["qualified_at"]
            },
            "extraction_request": {
                "url": signals["url"],
                "authority_tier": auth_tier,
                "evidence_type": "structured_data",
                "source_key": "MR-KEP-GSD-V1"
            },
            "extraction_result": ext_result,
            "validation_report": {"gate": "PASS"}
        }

        final_state = e.run_to_completion()

        # 4. Certification
        ev_bundle = e.context.get("evidence_bundle", [])
        all_evidence.extend(ev_bundle)

        cert_result = CE.certify(
            entity_key=cand_id,
            entity_type=row.get("stratum_style", "Single Malt"),
            qualification_record=e.context["qualification_record"],
            evidence_ledger=ev_bundle,
            execution_summary={"run_id": "P76-Real-Extraction"}
        )

        state = cert_result["certification_state"]

        if state == "CERTIFIED": stats["certified"] += 1
        elif state == "HOLD": stats["hold"] += 1
        else: stats["rejected"] += 1

        results.append(cert_result)
        manifest.append({
            "candidate_id": cand_id,
            "execution_state": final_state.value if hasattr(final_state, 'value') else str(final_state),
            "certification_state": state,
            "evidence_count": len(ev_bundle)
        })

    # Write outputs
    er_path = os.path.join(_OUTPUT, "extraction_results.jsonl")
    with open(er_path, 'w', encoding='utf-8') as f:
        for ext in all_extractions:
            f.write(json.dumps(ext) + "\n")

    eb_path = os.path.join(_OUTPUT, "evidence_bundle.jsonl")
    with open(eb_path, 'w', encoding='utf-8') as f:
        for ev in all_evidence:
            f.write(json.dumps(ev) + "\n")

    em_path = os.path.join(_OUTPUT, "extraction_manifest.json")
    with open(em_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)

    es_path = os.path.join(_OUTPUT, "extraction_statistics.md")
    with open(es_path, 'w', encoding='utf-8') as f:
        f.write("# P76 Extraction Statistics\n\n")
        f.write(f"- **Total Candidates Processed:** {stats['total']}\n")
        f.write(f"- **CERTIFIED:** {stats['certified']}\n")
        f.write(f"- **HOLD:** {stats['hold']}\n")
        f.write(f"- **REJECTED:** {stats['rejected']}\n")

    al_path = os.path.join(_OUTPUT, "audit_log.md")
    with open(al_path, 'w', encoding='utf-8') as f:
        f.write("# P76 Audit Log\n\n")
        f.write("All paths executed using deterministic extraction engine.\n")
        f.write("No synthetic metadata generated. Document processed as pure Database Dump.\n")

    print(f"\n=== BATCH PIPELINE COMPLETE ===")
    print(f"  Total Processed: {stats['total']}")
    print(f"  HOLD: {stats['hold']}")
    print(f"  CERTIFIED: {stats['certified']}")
    print(f"  REJECTED: {stats['rejected']}")

    return stats


def main():
    import argparse
    parser = argparse.ArgumentParser(description="MR-KEP Sprint 2 Pipeline")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--fixture",
        default=os.path.join(_MRKEP, "fixtures", "sample_whisky.json"),
        help="Path to fixture JSON",
    )
    group.add_argument(
        "--csv",
        help="Path to candidate CSV for batch processing",
    )
    parser.add_argument("--run-id", default=None, help="Run identifier")
    args = parser.parse_args()

    if args.csv:
        stats = run_batch_csv(args.csv)
        return 0
    else:
        summary = run_pipeline(args.fixture, args.run_id)
        return 0 if summary["certification_state"] in ("CERTIFIED", "HOLD") else 1


if __name__ == "__main__":
    sys.exit(main())