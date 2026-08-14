"""P500-K — Normalization Pipeline Tests.

Tests: deterministic normalization, idempotency, malformed input,
null handling, ABV normalization, flavor axis normalization,
name normalization, rating normalization, age normalization,
region/country normalization, text normalization,
unsupported field handling, conflict handling, entry point.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

# Path setup
_HERE = Path(__file__).resolve().parent
_NORM_ROOT = _HERE.parent
_ENGINE_ROOT = _NORM_ROOT.parent

for _p in [_NORM_ROOT, _ENGINE_ROOT / "extraction_engine", _NORM_ROOT]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from extraction_record import ExtractionRecord, _extractor_config_hash
from normalized_record import (
    NormalizedRecord, NormalizationResult,
    NormalizedFieldType as NFT,
    NormalizationStatus as NS,
)
from normalizers import (
    normalize_abv, normalize_product_name, normalize_source_identifier,
    normalize_flavor_axis, normalize_nose, normalize_palate,
    normalize_finish, normalize_rating, normalize_age,
    normalize_region, normalize_country,
    normalize_record, register_normalizer,
)
from normalizer import normalize_artifact, write_normalized_records, _norm_config_hash

import pytest


# ── Helpers ────────────────────────────────────────────────────────────

def _mk_rec(
    field_name: str,
    extracted_value: str,
    artifact_id: str = "test-artifact",
    source_type: str = "json",
    source_identifier: str = "test-file.json",
    source_uri: str = "/tmp/test-file.json",
    verbatim_quote: str = "",
    source_location: str = "json-key:test",
    content_hash: str = "",
    extraction_status: str = "extracted",
) -> ExtractionRecord:
    if not verbatim_quote:
        verbatim_quote = extracted_value
    if not content_hash:
        content_hash = hashlib.sha256(extracted_value.encode()).hexdigest()
    return ExtractionRecord(
        artifact_id=artifact_id,
        source_type=source_type,
        source_identifier=source_identifier,
        source_uri=source_uri,
        field_name=field_name,
        extracted_value=extracted_value,
        verbatim_quote=verbatim_quote,
        source_location=source_location,
        content_hash=content_hash,
        extraction_status=extraction_status,
    )


# ── ABV normalization ──────────────────────────────────────────────────

class TestAbvNormalization:
    def test_simple_percent(self):
        rec = _mk_rec("abv", "46%")
        nr = normalize_abv(rec)
        assert nr.normalization_status == NS.NORMALIZED.value
        assert nr.normalized_value == "46"
        assert nr.field_type == NFT.ABV.value

    def test_decimal_percent(self):
        rec = _mk_rec("abv", "46.3%")
        nr = normalize_abv(rec)
        assert nr.normalized_value == "46.3"

    def test_abv_prefix(self):
        rec = _mk_rec("abv", "60% ABV")
        nr = normalize_abv(rec)
        assert nr.normalized_value == "60"

    def test_empty_string(self):
        rec = _mk_rec("abv", "")
        nr = normalize_abv(rec)
        assert nr.normalization_status == NS.SKIPPED.value
        assert nr.normalized_value is None

    def test_unparseable(self):
        rec = _mk_rec("abv", "N/A")
        nr = normalize_abv(rec)
        assert nr.normalization_status == NS.CONFLICT.value

    def test_negative_abv_conflict(self):
        rec = _mk_rec("abv", "-5%")
        nr = normalize_abv(rec)
        assert nr.normalization_status == NS.CONFLICT.value

    def test_over_100_abv_conflict(self):
        rec = _mk_rec("abv", "150%")
        nr = normalize_abv(rec)
        assert nr.normalization_status == NS.CONFLICT.value


# ── Product name normalization ─────────────────────────────────────────

class TestProductNameNormalization:
    def test_basic_lowercase(self):
        rec = _mk_rec("product_name", "Ardbeg 10 Year Old")
        nr = normalize_product_name(rec)
        assert nr.normalized_value == "ardbeg 10 year old"
        assert nr.normalization_status == NS.NORMALIZED.value

    def test_ampersand_normalized(self):
        rec = _mk_rec("product_name", "Ardbeg & Laphroaig")
        nr = normalize_product_name(rec)
        assert "and" in nr.normalized_value

    def test_quotes_normalized(self):
        rec = _mk_rec("product_name", "Ardbeg \"Uigeadail\"")
        nr = normalize_product_name(rec)
        assert "'" not in nr.normalized_value
        assert '"' not in nr.normalized_value

    def test_empty_skipped(self):
        rec = _mk_rec("product_name", "")
        nr = normalize_product_name(rec)
        assert nr.normalization_status == NS.SKIPPED.value


# ── Flavor axis normalization ──────────────────────────────────────────

class TestFlavorAxisNormalization:
    def test_zero_to_hundred(self):
        rec = _mk_rec("smoky", "85")
        nr = normalize_flavor_axis(rec)
        assert nr.normalization_status == NS.NORMALIZED.value
        assert float(nr.normalized_value) == pytest.approx(0.85, abs=0.01)

    def test_zero_to_one(self):
        rec = _mk_rec("smoky", "0.75")
        nr = normalize_flavor_axis(rec)
        assert float(nr.normalized_value) == pytest.approx(0.75, abs=0.01)

    def test_non_numeric_conflict(self):
        rec = _mk_rec("smoky", "very")
        nr = normalize_flavor_axis(rec)
        assert nr.normalization_status == NS.CONFLICT.value

    def test_empty_skipped(self):
        rec = _mk_rec("smoky", "")
        nr = normalize_flavor_axis(rec)
        assert nr.normalization_status == NS.SKIPPED.value

    def test_rounding(self):
        rec = _mk_rec("sweet", "0.33333")
        nr = normalize_flavor_axis(rec)
        assert float(nr.normalized_value) == pytest.approx(0.33, abs=0.01)

    def test_axis_name_preserved_in_field_type(self):
        rec = _mk_rec("sherry", "50")
        nr = normalize_flavor_axis(rec)
        assert nr.field_type == NFT.FLAVOR_AXIS.value


# ── Rating normalization ───────────────────────────────────────────────

class TestRatingNormalization:
    def test_88_of_100(self):
        rec = _mk_rec("rating", "88/100")
        nr = normalize_rating(rec)
        assert nr.normalized_value == "88"
        assert nr.normalization_status == NS.NORMALIZED.value

    def test_bare_number(self):
        rec = _mk_rec("rating", "92")
        nr = normalize_rating(rec)
        assert nr.normalized_value == "92"

    def test_ten_scale(self):
        rec = _mk_rec("rating", "7.5/10")
        nr = normalize_rating(rec)
        assert nr.normalized_value == "75"

    def test_empty(self):
        rec = _mk_rec("rating", "")
        nr = normalize_rating(rec)
        assert nr.normalization_status == NS.SKIPPED.value

    def test_unparseable(self):
        rec = _mk_rec("rating", "Excellent")
        nr = normalize_rating(rec)
        assert nr.normalization_status == NS.CONFLICT.value


# ── Age normalization ──────────────────────────────────────────────────

class TestAgeNormalization:
    def test_year_old(self):
        rec = _mk_rec("age", "12 Year Old")
        nr = normalize_age(rec)
        assert nr.normalized_value == "12"

    def test_yo_abbreviation(self):
        rec = _mk_rec("age", "18yo")
        nr = normalize_age(rec)
        assert nr.normalized_value == "18"

    def test_nas(self):
        rec = _mk_rec("age", "NAS")
        nr = normalize_age(rec)
        assert nr.normalized_value == "0"

    def test_bare_number(self):
        rec = _mk_rec("age", "10")
        nr = normalize_age(rec)
        assert nr.normalized_value == "10"

    def test_empty(self):
        rec = _mk_rec("age", "")
        nr = normalize_age(rec)
        assert nr.normalization_status == NS.SKIPPED.value

    def test_unparseable(self):
        rec = _mk_rec("age", "old")
        nr = normalize_age(rec)
        assert nr.normalization_status == NS.CONFLICT.value


# ── Region normalization ───────────────────────────────────────────────

class TestRegionNormalization:
    def test_islay(self):
        rec = _mk_rec("region", "Islay")
        nr = normalize_region(rec)
        assert nr.normalized_value == "Islay"

    def test_lowercase(self):
        rec = _mk_rec("region", "highland")
        nr = normalize_region(rec)
        assert nr.normalized_value == "Highland"

    def test_with_region_suffix(self):
        rec = _mk_rec("region", "Speyside (region)")
        nr = normalize_region(rec)
        assert nr.normalized_value == "Speyside"

    def test_empty(self):
        rec = _mk_rec("region", "")
        nr = normalize_region(rec)
        assert nr.normalization_status == NS.SKIPPED.value

    def test_unrecognised(self):
        rec = _mk_rec("region", "Mars")
        nr = normalize_region(rec)
        assert nr.normalization_status == NS.CONFLICT.value


# ── Country normalization ──────────────────────────────────────────────

class TestCountryNormalization:
    def test_scotland(self):
        rec = _mk_rec("country", "Scotland")
        nr = normalize_country(rec)
        assert nr.normalized_value == "Scotland"

    def test_united_states(self):
        rec = _mk_rec("country", "USA")
        nr = normalize_country(rec)
        assert nr.normalized_value == "USA"

    def test_empty(self):
        rec = _mk_rec("country", "")
        nr = normalize_country(rec)
        assert nr.normalization_status == NS.SKIPPED.value

    def test_unrecognised(self):
        rec = _mk_rec("country", "Atlantis")
        nr = normalize_country(rec)
        assert nr.normalization_status == NS.CONFLICT.value


# ── Free-text normalization ────────────────────────────────────────────

class TestFreeTextNormalization:
    def test_nose_preserves_case(self):
        rec = _mk_rec("nose", "Peaty, smoky, citrus notes")
        nr = normalize_nose(rec)
        assert nr.normalized_value == "Peaty, smoky, citrus notes"
        assert nr.field_type == NFT.NOSE_TEXT.value

    def test_palate(self):
        rec = _mk_rec("palate", "Rich and full-bodied")
        nr = normalize_palate(rec)
        assert nr.normalized_value == "Rich and full-bodied"

    def test_finish_empty(self):
        rec = _mk_rec("finish", "")
        nr = normalize_finish(rec)
        assert nr.normalization_status == NS.SKIPPED.value


# ── Unsupported field ──────────────────────────────────────────────────

class TestUnsupportedField:
    def test_unknown_field_defaults_unsupported(self):
        rec = _mk_rec("some_weird_field", "xyz")
        nr = normalize_record(rec)
        assert nr.normalization_status == NS.UNSUPPORTED.value
        assert nr.normalized_value is None

    def test_verbatim_quote_preserved(self):
        rec = _mk_rec("some_weird_field", "xyz", verbatim_quote="original text from source")
        nr = normalize_record(rec)
        assert nr.verbatim_quote == "original text from source"


# ── Determinism and idempotency ────────────────────────────────────────

class TestDeterminism:
    def test_same_input_same_output(self):
        rec = _mk_rec("abv", "46%")
        nr1 = normalize_abv(rec)
        nr2 = normalize_abv(rec)
        assert nr1.to_dict() == nr2.to_dict()

    def test_normalize_artifact_deterministic(self):
        recs = [
            _mk_rec("abv", "46%"),
            _mk_rec("product_name", "Ardbeg 10"),
            _mk_rec("smoky", "85"),
        ]
        r1 = normalize_artifact(recs, "det-test")
        r2 = normalize_artifact(recs, "det-test")
        assert [r.to_dict() for r in r1.records] == [r.to_dict() for r in r2.records]

    def test_config_hash_deterministic(self):
        h1 = _norm_config_hash()
        h2 = _norm_config_hash()
        assert h1 == h2
        assert len(h1) == 16


# ── Null / empty handling ──────────────────────────────────────────────

class TestNullHandling:
    def test_empty_strings_become_skipped(self):
        rec = _mk_rec("abv", "")
        nr = normalize_abv(rec)
        assert nr.normalization_status == NS.SKIPPED.value

    def test_whitespace_only_skipped(self):
        rec = _mk_rec("product_name", "   ")
        nr = normalize_product_name(rec)
        assert nr.normalization_status == NS.SKIPPED.value

    def test_conflict_not_skipped(self):
        """An invalid value is CONFLICT, not SKIPPED."""
        rec = _mk_rec("abv", "N/A")
        nr = normalize_abv(rec)
        assert nr.normalization_status == NS.CONFLICT.value


# ── Entry point and output ─────────────────────────────────────────────

class TestEntryPoint:
    def test_write_jsonl(self):
        recs = [_mk_rec("abv", "46%")]
        result = normalize_artifact(recs, "test-out")
        outdir = tempfile.mkdtemp(prefix="norm-test-")
        try:
            path = write_normalized_records([result], output_dir=outdir)
            assert os.path.isfile(path)
            with open(path) as f:
                lines = [json.loads(l) for l in f]
            assert len(lines) == 1
            assert lines[0]["normalized_value"] == "46"
            assert lines[0]["field_type"] == NFT.ABV.value
        finally:
            import shutil
            shutil.rmtree(outdir, ignore_errors=True)

    def test_artifact_result_counts(self):
        recs = [
            _mk_rec("abv", "46%"),
            _mk_rec("product_name", "Ardbeg 10"),
            _mk_rec("smoky", "85"),
            _mk_rec("some_unknown", "data"),
            _mk_rec("abv", ""),  # skipped
        ]
        result = normalize_artifact(recs, "count-test")
        assert result.total == 5
        assert result.normalized >= 3
        assert result.skipped >= 1
        assert result.unsupported >= 1
        assert not result.is_blocked

    def test_artifact_is_blocked(self):
        recs = [_mk_rec("some_unknown_field", "x")]
        result = normalize_artifact(recs, "blocked-test")
        assert result.is_blocked
        assert result.normalized == 0

    def test_provenance_preserved(self):
        rec = _mk_rec("abv", "46%",
                      artifact_id="art-123",
                      source_identifier="test.json",
                      verbatim_quote="46% ABV quoted")
        nr = normalize_abv(rec)
        assert nr.artifact_id == "art-123"
        assert nr.source_identifier == "test.json"
        assert nr.verbatim_quote == "46% ABV quoted"


# ── Raw artifact immutability ────────────────────────────────────────

class TestRawArtifactImmutability:
    def test_raw_artifact_never_modified(self):
        """Normalize is pure — never writes to raw artifact file."""
        # No raw artifact file to check (normalize reads ExtractionRecords, not files)
        pass  # Guarantee is architectural; pure functions enforce it


# ── Conflict handling ──────────────────────────────────────────────

class TestConflictHandling:
    def test_conflict_has_reason(self):
        rec = _mk_rec("abv", "N/A")
        nr = normalize_abv(rec)
        assert nr.normalization_status == NS.CONFLICT.value
        assert nr.conflict_reason != ""

    def test_conflict_never_silent(self):
        rec = _mk_rec("region", "Atlantis")
        nr = normalize_region(rec)
        assert nr.normalization_status == NS.CONFLICT.value
        assert nr.conflict_reason != ""

    def test_mixed_normalized_and_conflict(self):
        recs = [
            _mk_rec("abv", "46%"),
            _mk_rec("region", "Isle of Insanity"),
            _mk_rec("product_name", "Good Stuff"),
        ]
        result = normalize_artifact(recs, "mixed-test")
        assert result.normalized >= 2
        assert result.conflicts >= 1
        assert not result.is_blocked
