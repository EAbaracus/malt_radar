#!/usr/bin/env python3
"""
MR-KEP Sprint 2 — End-to-End Integration Test

Verifies:
1. Deterministic output (identical second run)
2. Evidence references valid
3. Certification valid
4. Schema validation
5. No production interaction
6. Complete pipeline traversal
"""
import json
import os
import sys
import hashlib
import shutil
import tempfile
from pathlib import Path

# -- repo paths --
_HERE = os.path.dirname(os.path.abspath(__file__))
_MRKEP = os.path.dirname(_HERE)
_OUTPUT = os.path.join(_MRKEP, "output")
_FIXTURE = os.path.join(_MRKEP, "fixtures", "sample_whisky.json")

sys.path.insert(0, os.path.join(_MRKEP, "pipeline"))

import run as PIPELINE

PASS = 0
FAIL = 0


def check(name: str, condition: bool, detail: str = ""):
    global PASS, FAIL
    if condition:
        print(f"  ✓ {name}")
        PASS += 1
    else:
        print(f"  ✗ {name} — {detail}")
        FAIL += 1


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def test_full_pipeline():
    """Run the full pipeline once and verify all artifacts."""
    print("\n=== Phase 1: First Pipeline Run ===")
    summary = PIPELINE.run_pipeline(_FIXTURE, run_id="sprint2-integration-test")

    # All output files exist
    expected_files = [
        "qualification.json",
        "execution.json",
        "evidence.jsonl",
        "certification.json",
        "canonical_output.json",
        "run_manifest.json",
    ]

    print("\n--- 1. Artifact Existence ---")
    for fname in expected_files:
        fpath = os.path.join(_OUTPUT, fname)
        check(f"Output/{fname} exists", os.path.exists(fpath))

    # Load artifacts
    with open(os.path.join(_OUTPUT, "qualification.json")) as f:
        qual = json.load(f)
    with open(os.path.join(_OUTPUT, "execution.json")) as f:
        exec_summary = json.load(f)
    with open(os.path.join(_OUTPUT, "evidence.jsonl")) as f:
        evidence_lines = [json.loads(line) for line in f if line.strip()]
    with open(os.path.join(_OUTPUT, "certification.json")) as f:
        cert = json.load(f)
    with open(os.path.join(_OUTPUT, "canonical_output.json")) as f:
        canon = json.load(f)
    with open(os.path.join(_OUTPUT, "run_manifest.json")) as f:
        manifest = json.load(f)

    print("\n--- 2. Qualification Validation ---")
    check("qualification has schema_version", qual.get("schema_version") == "1.0.0")
    check("qualification has source_key", qual.get("source_key") == "whiskyfun")
    check("qualification has units array", isinstance(qual.get("units"), list) and len(qual["units"]) > 0)
    check("qualification has summary", "summary" in qual)

    for unit in qual["units"]:
        check(f"unit {unit.get('unit_id','')} has decision", unit.get("decision") in ("in_scope", "out_of_scope"))
        check(f"unit {unit.get('unit_id','')} has reason", bool(unit.get("reason")))

    in_scope = sum(1 for u in qual["units"] if u["decision"] == "in_scope")
    check("at least 1 in_scope unit", in_scope > 0)

    print("\n--- 3. Evidence Validation ---")
    check("evidence has entries", len(evidence_lines) > 0)
    for i, entry in enumerate(evidence_lines):
        eid = entry.get("evidence_id", "")
        check(f"evidence[{i}] has EV- id", eid.startswith("EV-") and len(eid) == 19)
        check(f"evidence[{i}] has provenance_state", entry.get("provenance_state") in (
            "discovered", "extracted", "normalized", "verified", "certified", "superseded", "deprecated"
        ))
        check(f"evidence[{i}] has valid entity_type", entry.get("entity_type") in (
            "distillery", "brand", "whisky", "bottling"
        ))
        check(f"evidence[{i}] has valid source_class", entry.get("source_class") in (
            "official", "regulatory", "official_wayback", "book", "expert_review",
            "structured_metadata", "community"
        ))
        check(f"evidence[{i}] has valid authority_tier", entry.get("authority_tier") in (
            "T1_authoritative", "T2_expert", "T3_community"
        ))
        # Required fields
        for req in ["schema_version", "evidence_id", "entity_type", "entity_id",
                     "field_name", "source_class", "source_name", "retrieval_timestamp",
                     "retrieval_hash", "confidence", "certification_level",
                     "review_status", "provenance_state"]:
            check(f"evidence[{i}] has {req}", req in entry)

    # Evidence IDs are unique
    eids = [e.get("evidence_id") for e in evidence_lines if e.get("evidence_id")]
    check(f"evidence IDs unique ({len(eids)} total)", len(eids) == len(set(eids)))

    print("\n--- 4. Execution Validation ---")
    check("execution has run_id", bool(exec_summary.get("run_id")))
    check("execution completed", exec_summary.get("final_state") in ("Completed", "COMPLETED", "Completed"))
    check("execution has retries", exec_summary.get("retries", -1) >= 0)

    print("\n--- 5. Certification Validation ---")
    check("certification has schema_version", cert.get("schema_version") == "1.0.0")
    check("certification has whisky_key", bool(cert.get("whisky_key")))
    check("certification has confidence_min", isinstance(cert.get("confidence_min"), (int, float)))
    check("certification state is valid", cert.get("certification_state") in ("CERTIFIED", "HOLD", "REJECTED"))
    check("certification has fields", isinstance(cert.get("fields"), dict) and len(cert["fields"]) > 0)
    check("certification has evidence_index", isinstance(cert.get("evidence_index"), list))
    check("certification has audit_status", cert.get("audit_status") == "pending_audit")

    # Every field has valid certification
    for fn, cinfo in cert.get("fields", {}).items():
        check(f"field '{fn}' has valid cert level", cinfo.get("certification_level") in (
            "certified", "proposed", "rejected", "uncertified"
        ))
        check(f"field '{fn}' has valid cert path", cinfo.get("certification_path") in (
            "A", "B", "C", "D", "E", "F", None
        ))
        check(f"field '{fn}' has authority_tier", cinfo.get("authority_tier") in (
            "T1_authoritative", "T2_expert", "T3_community", None
        ))
        check(f"field '{fn}' has confidence", isinstance(cinfo.get("confidence"), (int, float)))

    print("\n--- 6. Canonical Output Validation ---")
    check("canonical has schema_version", canon.get("schema_version") == "1.0.0")
    check("canonical has entity", "entity" in canon)
    check("canonical entity has type", canon.get("entity", {}).get("entity_type") == "whisky")
    check("canonical has metadata", "metadata" in canon)
    check("canonical has evidence", isinstance(canon.get("evidence"), list))
    check("canonical has provenance", "provenance" in canon)
    check("canonical provenance is deterministic", canon.get("provenance", {}).get("deterministic") is True)
    check("canonical has confidence", "confidence" in canon)
    check("canonical has certification", "certification" in canon)
    check("canonical has merge_candidates", isinstance(canon.get("merge_candidates"), list))

    # Metadata fields are present and typed correctly
    meta_fields = ["distillery_name", "region", "country", "abv", "age_statement",
                    "cask_type", "nose", "palate", "finish", "flavor_axes", "score"]
    for fname in meta_fields:
        check(f"canonical metadata has {fname}", fname in canon.get("metadata", {}))
    # ABV must be normalized to number (not string with %)
    abv_val = canon.get("metadata", {}).get("abv")
    check("canonical ABV is normalized to number", isinstance(abv_val, (int, float)) and abv_val == 46.0)

    # Evidence references in canonical are valid
    canon_eids = set(e.get("evidence_id") for e in canon.get("evidence", []))
    ledger_eids = set(e.get("evidence_id") for e in evidence_lines if e.get("evidence_id"))
    check("all canonical evidence refs exist in ledger", canon_eids.issubset(ledger_eids))

    print("\n--- 7. Manifest Validation ---")
    check("manifest has schema_version", manifest.get("schema_version") == "1.0.0")
    check("manifest has run_id", bool(manifest.get("run_id")))
    check("manifest has fixture hash", "sha256" in manifest.get("fixture", {}))
    check("manifest has all artifacts", len(manifest.get("artifacts", {})) == 5)

    # Verify artifact hashes
    for name, info in manifest.get("artifacts", {}).items():
        if os.path.exists(info.get("path", "")):
            actual_hash = _sha256_file(info["path"])
            check(f"manifest hash for {name} matches", actual_hash == info["sha256"])

    print("\n--- 8. No Production Interaction ---")
    # No production.db anywhere in output
    for root, dirs, files in os.walk(_OUTPUT):
        for f in files:
            check(f"no production.db in {f}", "production" not in f.lower())

    return PASS, FAIL


def test_deterministic():
    """Run the pipeline twice and verify identical output."""
    print("\n=== Phase 2: Deterministic Regression ===")
    run_id = "sprint2-det-test"
    fixed_ts = "2026-07-01T00:00:00Z"

    # First run with fixed timestamp
    PIPELINE.run_pipeline(_FIXTURE, run_id=run_id, fixed_timestamp=fixed_ts)

    # Snapshot first run
    first_run = {}
    for fname in ["qualification.json", "execution.json", "evidence.jsonl",
                    "certification.json", "canonical_output.json", "run_manifest.json"]:
        fpath = os.path.join(_OUTPUT, fname)
        if os.path.exists(fpath):
            with open(fpath, "rb") as f:
                first_run[fname] = f.read()

    # Second run with the SAME fixed timestamp
    PIPELINE.run_pipeline(_FIXTURE, run_id=run_id, fixed_timestamp=fixed_ts)

    # Compare
    for fname, first_content in first_run.items():
        fpath = os.path.join(_OUTPUT, fname)
        with open(fpath, "rb") as f:
            second_content = f.read()
        check(f"deterministic: {fname} identical", first_content == second_content,
              "files differ between runs")

    return PASS, FAIL


def test_evidence_references():
    """Verify every certification evidence_index references valid ledger entries."""
    print("\n=== Phase 3: Evidence Reference Integrity ===")

    # Load artifacts
    with open(os.path.join(_OUTPUT, "evidence.jsonl")) as f:
        ledger = [json.loads(line) for line in f if line.strip()]
    with open(os.path.join(_OUTPUT, "certification.json")) as f:
        cert = json.load(f)

    ledger_eids = set(e.get("evidence_id") for e in ledger if e.get("evidence_id"))
    cert_eids = set(e.get("evidence_id") for e in cert.get("evidence_index", []) if e.get("evidence_id"))

    check("cert evidence refs subset of ledger", cert_eids.issubset(ledger_eids),
          f"{len(cert_eids - ledger_eids)} missing evidence_ids")

    return PASS, FAIL


def test_schema_validation():
    """Validate output against JSON schemas."""
    print("\n=== Phase 4: Schema Validation ===")

    try:
        import jsonschema
    except ImportError:
        print("  ⚠ jsonschema not installed — skipping schema validation")
        return PASS, FAIL

    # Load schemas
    qual_schema_path = os.path.join(_MRKEP, "schemas", "qualification.schema.json")
    # cert_schema_path = os.path.join(_MRKEP, "schemas", "certification.schema.json")
    canon_schema_path = os.path.join(_MRKEP, "extraction", "canonical_output.schema.json")

    with open(qual_schema_path) as f:
        qual_schema = json.load(f)
    # with open(cert_schema_path) as f:
    #     cert_schema = json.load(f)
    with open(canon_schema_path) as f:
        canon_schema = json.load(f)

    # Load outputs
    with open(os.path.join(_OUTPUT, "qualification.json")) as f:
        qual = json.load(f)
    with open(os.path.join(_OUTPUT, "canonical_output.json")) as f:
        canon = json.load(f)

    # Validate qualification
    qual_errors = list(jsonschema.Draft7Validator(qual_schema).iter_errors(qual))
    check("qualification schema valid", len(qual_errors) == 0,
          f"{len(qual_errors)} errors: {qual_errors[:3]}")

    # Validate canonical output
    canon_errors = list(jsonschema.Draft7Validator(canon_schema).iter_errors(canon))
    check("canonical output schema valid", len(canon_errors) == 0,
          f"{len(canon_errors)} errors: {canon_errors[:3]}")

    return PASS, FAIL


def main():
    global PASS, FAIL
    PASS = 0
    FAIL = 0

    print("=" * 60)
    print("MR-KEP Sprint 2 — End-to-End Integration Test")
    print("=" * 60)

    # Phase 1: Full pipeline
    test_full_pipeline()

    # Phase 2: Deterministic
    test_deterministic()

    # Phase 3: Evidence references
    test_evidence_references()

    # Phase 4: Schema validation
    test_schema_validation()

    # Summary
    print("\n" + "=" * 60)
    print(f"RESULTS: {PASS} passed, {FAIL} failed")
    print("=" * 60)

    if FAIL > 0:
        print("\n⚠  Some checks FAILED — review details above")
    else:
        print("\n✓ ALL CHECKS PASSED")

    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())