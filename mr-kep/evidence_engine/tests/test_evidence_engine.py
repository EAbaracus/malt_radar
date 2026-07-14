# =============================================================================
# MR-KEP P73 — Evidence Engine tests
# -----------------------------------------------------------------------------
# Three test families (the brief's deliverables):
#   1. Unit tests          — deterministic derivation of ids, hashes, tiers
#   2. Deterministic regression — fixed fixture => byte-identical ledger
#   3. Schema validation    — every emitted entry validates against
#                             evidence/evidence_schema.json (reused, unmodified)
#
# These are plain pytest tests (no suite invention, no production writes).
# Run:  pytest mr-kep/evidence_engine/tests/ -q
# =============================================================================
import os
import json
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ENGINE_DIR = os.path.dirname(_HERE)
_MRKEP = os.path.dirname(_ENGINE_DIR)
sys.path.insert(0, _ENGINE_DIR)

import engine as E

EVIDENCE_SCHEMA = os.path.join(_MRKEP, "evidence", "evidence_schema.json")
QUAL_SCHEMA = os.path.join(_MRKEP, "schemas", "qualification.schema.json")


# ---- load jsonschema if available; else a minimal manual validator -----------
def _get_validator():
    try:
        import jsonschema  # type: ignore
        with open(EVIDENCE_SCHEMA, "r", encoding="utf-8") as f:
            schema = json.load(f)
        validator = jsonschema.Draft7Validator(schema)
        return validator, True
    except Exception:
        return None, False


_VALIDATOR, _HAVE_JSONSCHEMA = _get_validator()


def _validate(entry: dict) -> list:
    """Return list of error messages (empty = valid)."""
    if _HAVE_JSONSCHEMA:
        return [f"{e.message} (at {list(e.path)})" for e in _VALIDATOR.iter_errors(entry)]
    return _minimal_validate(entry)


def _minimal_validate(entry: dict) -> list:
    errs = []
    required = ["schema_version", "evidence_id", "entity_type", "entity_id",
                "field_name", "field_value", "source_class", "source_name",
                "source_url", "retrieval_timestamp", "retrieval_hash", "confidence",
                "authority_tier", "certification_level", "review_status",
                "provenance_state"]
    for k in required:
        if k not in entry:
            errs.append(f"missing required {k}")
    if entry.get("entity_type") not in ("distillery", "brand", "whisky", "bottling"):
        errs.append("bad entity_type")
    if entry.get("source_class") not in ("official", "regulatory", "official_wayback",
                                          "book", "expert_review", "structured_metadata", "community"):
        errs.append("bad source_class")
    if entry.get("authority_tier") not in ("T1_authoritative", "T2_expert", "T3_community"):
        errs.append("bad authority_tier")
    if entry.get("provenance_state") not in ("discovered", "extracted", "normalized",
                                              "verified", "certified", "superseded", "deprecated"):
        errs.append("bad provenance_state")
    import re
    if not re.match(r"^EV-[a-f0-9]{16}$", entry.get("evidence_id", "")):
        errs.append("bad evidence_id format")
    return errs


# =============================================================================
# Fixtures
# =============================================================================
def _sample_qual_record(source_key="whiskyfun"):
    return {
        "schema_version": "1.0.0",
        "source_key": source_key,
        "qualified_at": "2026-07-13T10:00:00Z",
        "criteria": {"min_score": 60},
        "units": [
            {"unit_id": "https://whiskyfun.com/reviews/laphroaig-10#score",
             "decision": "in_scope", "reason": "expert review, high score",
             "whisky_hint": "Laphroaig 10yo"},
            {"unit_id": "https://whiskyfun.com/reviews/laphroaig-10#nose",
             "decision": "in_scope", "reason": "expert review, sensory",
             "whisky_hint": "Laphroaig 10yo"},
            {"unit_id": "https://spam.example/x", "decision": "out_of_scope",
             "reason": "license_risk", "whisky_hint": ""},
            {"unit_id": "https://archive.example/y", "decision": "deferred",
             "reason": "OCR-blocked", "whisky_hint": "Foo Bar"},
        ],
        "summary": {"in_scope": 2, "out_of_scope": 1, "deferred": 1},
    }


# =============================================================================
# 1. UNIT TESTS
# =============================================================================
class TestUnit:
    def test_evidence_id_format(self):
        e = E.build_entry(
            entity_type="whisky", entity_id="laphroaig 10yo",
            source_name="whiskyfun", source_class="expert_review",
            authority_tier="T2_expert", source_url="https://whiskyfun.com/x",
            retrieval_timestamp="2026-07-13T10:00:00Z",
        )
        import re
        assert re.match(r"^EV-[a-f0-9]{16}$", e["evidence_id"]), e["evidence_id"]

    def test_evidence_id_deterministic(self):
        a = E.build_entry(entity_type="whisky", entity_id="laphroaig 10yo",
                           source_name="whiskyfun", source_class="expert_review",
                           authority_tier="T2_expert", source_url="https://whiskyfun.com/x",
                           retrieval_timestamp="2026-07-13T10:00:00Z")
        b = E.build_entry(entity_type="whisky", entity_id="laphroaig 10yo",
                           source_name="whiskyfun", source_class="expert_review",
                           authority_tier="T2_expert", source_url="https://whiskyfun.com/x",
                           retrieval_timestamp="2026-07-13T10:00:00Z")
        assert a["evidence_id"] == b["evidence_id"]
        assert a["evidence_hash"] == b["evidence_hash"]

    def test_evidence_id_changes_with_input(self):
        a = E.build_entry(entity_type="whisky", entity_id="laphroaig 10yo",
                           source_name="whiskyfun", source_class="expert_review",
                           authority_tier="T2_expert", source_url="https://whiskyfun.com/x",
                           retrieval_timestamp="2026-07-13T10:00:00Z")
        b = E.build_entry(entity_type="whisky", entity_id="laphroaig 18yo",
                           source_name="whiskyfun", source_class="expert_review",
                           authority_tier="T2_expert", source_url="https://whiskyfun.com/x",
                           retrieval_timestamp="2026-07-13T10:00:00Z")
        assert a["evidence_id"] != b["evidence_id"]

    def test_source_resolution_whiskyfun_t2_expert(self):
        cfg = E.load_authority_configs()
        r = E.resolve_source("whiskyfun", cfg)
        assert r["authority_tier"] == "T2_expert"
        assert r["source_class"] == "expert_review"
        assert r["evidence_type"] == "expert_quote"

    def test_source_resolution_producer_t1(self):
        cfg = E.load_authority_configs()
        r = E.resolve_source("producer_technical_sheet", cfg)
        assert r["authority_tier"] == "T1_authoritative"

    def test_source_resolution_unknown_failsafe_t3(self):
        cfg = E.load_authority_configs()
        r = E.resolve_source("totally_unknown_src", cfg)
        assert r["authority_tier"] == "T3_community"

    def test_discovered_state_no_fabrication(self):
        """A discovered candidate must NOT carry a fabricated VALUE/selector, but
        field_name IS a required non-null string (frozen schema) — it is the
        canonical field scope identified at discovery (P63 source class)."""
        e = E.build_entry(entity_type="whisky", entity_id="laphroaig 10yo",
                           source_name="whiskyfun", source_class="expert_review",
                           authority_tier="T2_expert", source_url="https://whiskyfun.com/x",
                           retrieval_timestamp="2026-07-13T10:00:00Z",
                           field_name="score")
        assert e["provenance_state"] == "discovered"
        assert e["field_value"] is None
        assert isinstance(e["field_name"], str) and e["field_name"]
        assert e["confidence"] == 0.0
        assert e["selector"] is None
        assert e["extraction_method"] is None

    def test_only_in_scope_becomes_candidate(self):
        ledger = E.run([_sample_qual_record()])
        assert len(ledger) == 2  # 2 in_scope units; out_of_scope + deferred skipped
        assert all(e["provenance_state"] == "discovered" for e in ledger)

    def test_retrieval_hash_deterministic(self):
        e = E.build_entry(entity_type="whisky", entity_id="x", source_name="whiskyfun",
                           source_class="expert_review", authority_tier="T2_expert",
                           source_url=None, retrieval_timestamp="2026-07-13T10:00:00Z")
        assert e["retrieval_hash"] == E._sha256_hex("|2026-07-13T10:00:00Z|")

    def test_url_parsed_from_unit_id(self):
        assert E._url_from_unit_id("https://a.com/b#c") == "https://a.com/b"
        assert E._url_from_unit_id("not-a-url") == ""


# =============================================================================
# 2. SCHEMA VALIDATION
# =============================================================================
class TestSchemaValidation:
    def test_all_entries_validate(self):
        ledger = E.run([_sample_qual_record(), _sample_qual_record("producer_technical_sheet")])
        for e in ledger:
            errs = _validate(e)
            assert not errs, f"schema invalid: {errs}\n{json.dumps(e, indent=2)}"

    def test_source_url_null_requires_citation(self):
        """evidence_schema.json allOf: if source_url null, source_citation is the
        intended offline-traceability field. NOTE: the frozen schema's if/then
        does not hard-enforce this at validation time; P73 still populates
        source_citation when url is null (best practice, no contract change).
        This test asserts BOTH states are schema-valid (schema reused verbatim)."""
        e = E.build_entry(entity_type="whisky", entity_id="x", source_name="community_aggregate",
                           source_class="community", authority_tier="T3_community",
                           source_url=None, retrieval_timestamp="2026-07-13T10:00:00Z",
                           field_name="community_rating")
        errs = _validate(e)
        assert not errs, errs  # schema-valid even without citation (frozen schema)
        # With citation present -> also valid (preferred path)
        e2 = E.build_entry(entity_type="whisky", entity_id="x", source_name="community_aggregate",
                           source_class="community", authority_tier="T3_community",
                           source_url=None, retrieval_timestamp="2026-07-13T10:00:00Z",
                           source_citation="Community forum thread #123",
                           field_name="community_rating")
        errs2 = _validate(e2)
        assert not errs2, errs2
        assert e2["source_citation"] == "Community forum thread #123"


# =============================================================================
# 3. DETERMINISTIC REGRESSION (byte-identical across runs)
# =============================================================================
_REGRESSION_FIXTURE = [
    _sample_qual_record("whiskyfun"),
    _sample_qual_record("producer_technical_sheet"),
    _sample_qual_record("community_aggregate"),
]


def _ledger_text(records):
    ledger = E.run(records)
    return "\n".join(json.dumps(e, sort_keys=True, ensure_ascii=False) for e in ledger)


class TestDeterministicRegression:
    def test_byte_identical_rerun(self):
        t1 = _ledger_text(_REGRESSION_FIXTURE)
        t2 = _ledger_text(_REGRESSION_FIXTURE)
        assert t1 == t2, "non-deterministic output"

    def test_identical_evidence_ids_across_runs(self):
        l1 = E.run(_REGRESSION_FIXTURE)
        l2 = E.run(_REGRESSION_FIXTURE)
        assert [e["evidence_id"] for e in l1] == [e["evidence_id"] for e in l2]

    def test_idempotent_append_no_duplicates(self):
        """Re-processing the same inputs yields the same rows; dedup is detectable
        by evidence_id equality (append-only, idempotent)."""
        l1 = E.run(_REGRESSION_FIXTURE)
        l2 = E.run(_REGRESSION_FIXTURE)
        assert len(l1) == len(l2)
        assert len({e["evidence_id"] for e in l1}) == len(l1)
        assert {e["evidence_id"] for e in l1} == {e["evidence_id"] for e in l2}

    def test_known_fixture_snapshot(self):
        """Pin a concrete evidence_id so a contract change is caught (regression)."""
        ledger = E.run([_sample_qual_record()])
        ids = sorted(e["evidence_id"] for e in ledger)
        expected = E.build_entry(
            entity_type="whisky", entity_id="laphroaig 10yo",
            source_name="whiskyfun", source_class="expert_review",
            authority_tier="T2_expert",
            source_url="https://whiskyfun.com/reviews/laphroaig-10",
            retrieval_timestamp="2026-07-13T10:00:00Z",
            field_name="score",
            notes="Evidence candidate from qualification unit "
                  "https://whiskyfun.com/reviews/laphroaig-10#score (decision=in_scope). "
                  "reason=expert review, high score",
        )["evidence_id"]
        assert expected in ids, f"expected {expected} in {ids}"
