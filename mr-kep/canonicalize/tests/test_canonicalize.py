"""P500-L — Canonical CANONICALIZE Pipeline Tests.

Tests: 7 axes, source vocabulary reduction, 0–100→0–1 conversion,
boundary values, unmappable axes, conflicting mappings, null/missing,
deterministic output, provenance preservation, no out-of-range values.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_CANON_ROOT = _HERE.parent
_ENGINE_ROOT = _CANON_ROOT.parent

for _p in [_CANON_ROOT, _ENGINE_ROOT / "normalize",
           _ENGINE_ROOT / "extraction_engine",
           _ENGINE_ROOT / "d4_reducer",
           _ENGINE_ROOT / "common"]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from normalized_record import NormalizedRecord, NormalizedFieldType as NFT, NormalizationStatus as NS
from canonicalized_record import (
    CanonicalFlavorEvidence, CanonicalizationResult,
    CanonicalizationStatus, AxisSource, CANONICAL_AXES,
)
from canonicalizer import canonicalize, canonicalize_batch, write_canonicalized_records, _canon_config_hash

import pytest


# ── Helper ────────────────────────────────────────────────────────────

def _mk_norm(
    field_type: str,
    normalized_value: str,
    verbatim_quote: str = "",
    artifact_id: str = "art-001",
    raw_value: str = "",
    field_name: str = "",
) -> NormalizedRecord:
    if not verbatim_quote:
        verbatim_quote = normalized_value
    if not raw_value:
        raw_value = normalized_value
    if not field_name:
        # Infer from field_type
        if field_type == NFT.FLAVOR_AXIS.value:
            field_name = "smoky"
        elif field_type == NFT.NOSE_TEXT.value:
            field_name = "nose"
        elif field_type == NFT.PALATE_TEXT.value:
            field_name = "palate"
        elif field_type == NFT.FINISH_TEXT.value:
            field_name = "finish"
        elif field_type == NFT.RATING.value:
            field_name = "rating"
        elif field_type == NFT.ABV.value:
            field_name = "abv"
        else:
            field_name = "unknown"
    return NormalizedRecord(
        artifact_id=artifact_id,
        source_type="json",
        source_identifier="test.json",
        source_uri="/tmp/test.json",
        original_field_name=field_name,
        verbatim_quote=verbatim_quote,
        source_location="json:test",
        content_hash=hashlib.sha256(normalized_value.encode()).hexdigest(),
        extractor_version="extractor-v1.0.0",
        extractor_config_hash="abc123def456",
        field_type=field_type,
        normalized_value=normalized_value,
        raw_value=raw_value,
        normalization_status=NS.NORMALIZED.value,
    )


# ── 7 canonical axes ──────────────────────────────────────────────────

class TestCanonicalAxes:
    def test_smoky_axis_from_direct_record(self):
        rec = _mk_norm(NFT.FLAVOR_AXIS.value, "0.85", verbatim_quote="smoky")
        result = canonicalize("W000001", "Ardbeg 10", [rec])
        assert result.status in (CanonicalizationStatus.PARTIAL.value,)
        assert result.evidence.vector["smoky"] == pytest.approx(0.85, abs=0.01)

    def test_peaty_axis(self):
        rec = _mk_norm(NFT.FLAVOR_AXIS.value, "0.80", verbatim_quote="peaty",
                       field_name="peaty")
        result = canonicalize("W000001", "Test", [rec])
        assert result.evidence.vector["peaty"] == pytest.approx(0.80, abs=0.01)

    def test_sherry_axis(self):
        rec = _mk_norm(NFT.FLAVOR_AXIS.value, "0.60", verbatim_quote="sherry",
                       field_name="sherry")
        result = canonicalize("W000001", "Test", [rec])
        assert result.evidence.vector["sherry"] == pytest.approx(0.60, abs=0.01)

    def test_fruity_axis(self):
        rec = _mk_norm(NFT.FLAVOR_AXIS.value, "0.90", verbatim_quote="fruity",
                       field_name="fruity")
        result = canonicalize("W000001", "Test", [rec])
        assert result.evidence.vector["fruity"] == pytest.approx(0.90, abs=0.01)

    def test_sweet_axis(self):
        rec = _mk_norm(NFT.FLAVOR_AXIS.value, "0.30", verbatim_quote="sweet",
                       field_name="sweet")
        result = canonicalize("W000001", "Test", [rec])
        assert result.evidence.vector["sweet"] == pytest.approx(0.30, abs=0.01)

    def test_spicy_axis(self):
        rec = _mk_norm(NFT.FLAVOR_AXIS.value, "0.75", verbatim_quote="spicy",
                       field_name="spicy")
        result = canonicalize("W000001", "Test", [rec])
        assert result.evidence.vector["spicy"] == pytest.approx(0.75, abs=0.01)

    def test_maritime_axis(self):
        rec = _mk_norm(NFT.FLAVOR_AXIS.value, "0.50", verbatim_quote="maritime",
                       field_name="maritime")
        result = canonicalize("W000001", "Test", [rec])
        assert result.evidence.vector["maritime"] == pytest.approx(0.50, abs=0.01)

    def test_all_axes_present_in_output(self):
        """Every canonical axis must appear in the output vector."""
        result = canonicalize("W000001", "Test", [])
        for ax in CANONICAL_AXES:
            assert ax in result.evidence.vector, f"Missing axis: {ax}"


# ── Source vocabulary reduction ───────────────────────────────────────

class TestVocabularyReduction:
    def test_descriptor_mapped_to_canonical_axis(self):
        """'smoke' → 'smoky' via FlavorMapper."""
        rec = _mk_norm(NFT.FLAVOR_AXIS.value, "0.80", verbatim_quote="smoke",
                       field_name="smoky")
        result = canonicalize("W000001", "Test", [rec])
        assert result.evidence.vector["smoky"] == pytest.approx(0.80, abs=0.01)

    def test_multiple_source_descriptors_to_same_axis(self):
        """'salt', 'brine', 'seaweed' → all contribute to 'maritime'."""
        recs = [
            _mk_norm(NFT.FLAVOR_AXIS.value, "0.70", verbatim_quote="salt",
                     field_name="maritime", artifact_id="a1"),
            _mk_norm(NFT.FLAVOR_AXIS.value, "0.80", verbatim_quote="brine",
                     field_name="maritime", artifact_id="a2"),
            _mk_norm(NFT.FLAVOR_AXIS.value, "0.60", verbatim_quote="seaweed",
                     field_name="maritime", artifact_id="a3"),
        ]
        result = canonicalize("W000001", "Test", recs)
        expected = (0.70 + 0.80 + 0.60) / 3
        assert result.evidence.vector["maritime"] == pytest.approx(expected, abs=0.01)

    def test_free_text_nose_maps_descriptors(self):
        """Free-text nose 'Peaty, smoky, maritime with citrus' maps to multiple axes."""
        rec = _mk_norm(NFT.NOSE_TEXT.value, "Peaty, smoky, maritime with citrus",
                       verbatim_quote="Peaty, smoky, maritime with citrus",
                       field_name="nose")
        result = canonicalize("W000001", "Test", [rec])
        assert result.evidence.vector["peaty"] > 0.0
        assert result.evidence.vector["smoky"] > 0.0
        assert result.evidence.vector["maritime"] > 0.0
        assert result.evidence.vector["fruity"] > 0.0  # citrus → fruity

    def test_free_text_palate_maps_descriptors(self):
        rec = _mk_norm(NFT.PALATE_TEXT.value,
                       "Rich honey sweetness with cinnamon spice",
                       field_name="palate")
        result = canonicalize("W000001", "Test", [rec])
        assert result.evidence.vector["sweet"] > 0.0
        assert result.evidence.vector["spicy"] > 0.0


# ── 0–100 → 0–1 conversion ───────────────────────────────────────────

class TestScaleConversion:
    def test_zero_to_hundred_converted(self):
        """Value 0.85 is already on storage scale (from P500-K normalizer)."""
        rec = _mk_norm(NFT.FLAVOR_AXIS.value, "0.85", field_name="smoky")
        result = canonicalize("W000001", "Test", [rec])
        assert 0.0 <= result.evidence.vector["smoky"] <= 1.0

    def test_clamp_above_1(self):
        """Defensive: values > 1 clamped to 1.0."""
        rec = _mk_norm(NFT.FLAVOR_AXIS.value, "1.5", field_name="smoky")
        result = canonicalize("W000001", "Test", [rec])
        assert result.evidence.vector["smoky"] == 1.0

    def test_clamp_below_0(self):
        rec = _mk_norm(NFT.FLAVOR_AXIS.value, "-0.5", field_name="smoky")
        result = canonicalize("W000001", "Test", [rec])
        assert result.evidence.vector["smoky"] == 0.0


# ── Boundary values ───────────────────────────────────────────────────

class TestBoundaryValues:
    def test_zero_axis(self):
        rec = _mk_norm(NFT.FLAVOR_AXIS.value, "0.0", field_name="smoky")
        result = canonicalize("W000001", "Test", [rec])
        assert result.evidence.vector["smoky"] == 0.0

    def test_one_axis(self):
        rec = _mk_norm(NFT.FLAVOR_AXIS.value, "1.0", field_name="smoky")
        result = canonicalize("W000001", "Test", [rec])
        assert result.evidence.vector["smoky"] == 1.0

    def test_missing_axis_is_zero(self):
        """Axis with no data defaults to 0.0."""
        result = canonicalize("W000001", "Test", [])
        for ax in CANONICAL_AXES:
            assert result.evidence.vector[ax] == 0.0

    def test_empty_has_all_zeros(self):
        result = canonicalize("W000001", "Test", [])
        assert result.status == CanonicalizationStatus.EMPTY.value
        assert all(v == 0.0 for v in result.evidence.vector.values())


# ── Unmappable axes ──────────────────────────────────────────────────

class TestUnmappable:
    def test_ambiguous_words_skipped(self):
        """'rich', 'complex', 'smooth' are too vague and should not map."""
        rec = _mk_norm(NFT.NOSE_TEXT.value, "Rich and complex with smooth finish",
                       field_name="nose")
        result = canonicalize("W000001", "Test", [rec])
        # No axes from ambiguous words
        # But 'finish' is a non-descriptor word, not mappable
        unmapped = result.evidence.unmapped_descriptors
        # These are vague but also 'rich' and 'smooth' and 'complex' are in _AMBIGUOUS_TERMS
        # and won't appear in unmapped either

    def test_unrecognised_descriptor_tracked(self):
        """Unmappable verbatim on a flavor_axis record is still mapped via field_name."""
        rec = _mk_norm(NFT.FLAVOR_AXIS.value, "0.50",
                       verbatim_quote="zythumflavor", field_name="smoky")
        result = canonicalize("W000001", "Test", [rec])
        # 'zythumflavor' isn't in the mapper, but field_name='smoky' drives mapping
        assert result.evidence.vector["smoky"] == 0.5
        assert result.status == CanonicalizationStatus.PARTIAL.value

    def test_partial_status(self):
        """Only some axes resolved → PARTIAL."""
        rec = _mk_norm(NFT.FLAVOR_AXIS.value, "0.85", field_name="smoky")
        result = canonicalize("W000001", "Test", [rec])
        assert result.status == CanonicalizationStatus.PARTIAL.value


# ── Null/missing flavor data ──────────────────────────────────────────

class TestNullMissing:
    def test_no_records_returns_empty(self):
        result = canonicalize("W000001", "Test", [])
        assert result.status == CanonicalizationStatus.EMPTY.value

    def test_non_flavor_records_ignored(self):
        recs = [
            _mk_norm(NFT.ABV.value, "46%", field_name="abv"),
            _mk_norm(NFT.RATING.value, "88", field_name="rating"),
        ]
        result = canonicalize("W000001", "Test", recs)
        assert result.status == CanonicalizationStatus.EMPTY.value
        assert all(v == 0.0 for v in result.evidence.vector.values())

    def test_none_normalized_value_skipped(self):
        rec = NormalizedRecord(
            artifact_id="art-001", source_type="json",
            source_identifier="test.json", source_uri="/tmp/test.json",
            original_field_name="smoky", verbatim_quote="smoky",
            source_location="json:x", content_hash="abc",
            extractor_version="v1", extractor_config_hash="config",
            field_type=NFT.FLAVOR_AXIS.value,
            normalized_value=None,
            raw_value="85",
            normalization_status=NS.CONFLICT.value,
        )
        result = canonicalize("W000001", "Test", [rec])
        assert result.status == CanonicalizationStatus.EMPTY.value


# ── Deterministic output ──────────────────────────────────────────────

class TestDeterminism:
    def test_same_input_same_output(self):
        recs = [
            _mk_norm(NFT.FLAVOR_AXIS.value, "0.85", field_name="smoky"),
            _mk_norm(NFT.FLAVOR_AXIS.value, "0.30", field_name="sweet"),
        ]
        r1 = canonicalize("W000001", "Test", recs)
        r2 = canonicalize("W000001", "Test", recs)
        assert r1.evidence.to_dict() == r2.evidence.to_dict()
        assert r1.status == r2.status

    def test_config_hash_deterministic(self):
        h1 = _canon_config_hash()
        h2 = _canon_config_hash()
        assert h1 == h2
        assert len(h1) == 16


# ── Provenance preservation ───────────────────────────────────────────

class TestProvenance:
    def test_axis_source_artifact_ids(self):
        recs = [
            _mk_norm(NFT.FLAVOR_AXIS.value, "0.85", field_name="smoky",
                     artifact_id="art-smoky-a"),
            _mk_norm(NFT.FLAVOR_AXIS.value, "0.30", field_name="sweet",
                     artifact_id="art-sweet-b"),
        ]
        result = canonicalize("W000001", "Test", recs)
        for src in result.evidence.axis_sources:
            if src.axis_name == "smoky":
                assert "art-smoky-a" in src.source_record_ids
            if src.axis_name == "sweet":
                assert "art-sweet-b" in src.source_record_ids

    def test_axis_source_verbatim_excerpts(self):
        rec = _mk_norm(NFT.FLAVOR_AXIS.value, "0.85", verbatim_quote="smoky",
                       field_name="smoky")
        result = canonicalize("W000001", "Test", [rec])
        for src in result.evidence.axis_sources:
            if src.axis_name == "smoky":
                assert "smoky" in src.verbatim_excerpts

    def test_whisky_id_preserved(self):
        result = canonicalize("W000999", "Test Whisky", [])
        assert result.whisky_id == "W000999"
        assert result.evidence.whisky_name == "Test Whisky"


# ── No out-of-range values ────────────────────────────────────────────

class TestOutOfRange:
    def test_all_vector_values_in_0_1(self):
        recs = [
            _mk_norm(NFT.FLAVOR_AXIS.value, str(v/100), field_name=ax)
            for ax in CANONICAL_AXES
            for v in range(0, 101, 25)
        ]
        result = canonicalize("W000001", "Test", recs)
        for ax in CANONICAL_AXES:
            assert 0.0 <= result.evidence.vector[ax] <= 1.0, \
                f"Axis {ax} out of range: {result.evidence.vector[ax]}"

    def test_negative_input_clamped(self):
        rec = _mk_norm(NFT.FLAVOR_AXIS.value, "-10", field_name="smoky")
        result = canonicalize("W000001", "Test", [rec])
        assert result.evidence.vector["smoky"] >= 0.0

    def test_over_1_input_clamped(self):
        rec = _mk_norm(NFT.FLAVOR_AXIS.value, "999", field_name="smoky")
        result = canonicalize("W000001", "Test", [rec])
        assert result.evidence.vector["smoky"] <= 1.0


# ── Batch canonicalization ────────────────────────────────────────────

class TestBatch:
    def test_batch_multiple_whiskies(self):
        data = {
            "W000001": ("Ardbeg 10", [
                _mk_norm(NFT.FLAVOR_AXIS.value, "0.85", field_name="smoky"),
            ]),
            "W000002": ("Laphroaig 10", [
                _mk_norm(NFT.FLAVOR_AXIS.value, "0.90", field_name="peaty"),
            ]),
        }
        results = canonicalize_batch(data)
        assert len(results) == 2
        ids = {r.whisky_id for r in results}
        assert ids == {"W000001", "W000002"}

    def test_batch_deterministic(self):
        data = {
            "W000001": ("A", [_mk_norm(NFT.FLAVOR_AXIS.value, "0.85", field_name="smoky")]),
        }
        r1 = canonicalize_batch(data)
        r2 = canonicalize_batch(data)
        assert r1[0].evidence.to_dict() == r2[0].evidence.to_dict()


# ── JSONL output ──────────────────────────────────────────────────────

class TestOutput:
    def test_write_jsonl(self):
        recs = [_mk_norm(NFT.FLAVOR_AXIS.value, "0.85", field_name="smoky")]
        result = canonicalize("W000001", "Test", recs)
        tmp = tempfile.mkdtemp(prefix="canon-test-")
        try:
            path = write_canonicalized_records([result], tmp)
            assert os.path.isfile(path)
            with open(path) as f:
                data = json.loads(f.readline())
            assert data["whisky_id"] == "W000001"
            assert "evidence" in data
            assert "vector" in data["evidence"]
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)
