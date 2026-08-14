"""Normalization pipeline — canonical entry point (P500-K).

Usage:
    python -m mr-kep.normalize.normalizer <extraction_output_path>

Or programmatically:
    from normalize.normalizer import normalize_artifact
    result = normalize_artifact(extraction_records, artifact_id)
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Path setup
_ENGINE_ROOT = Path(__file__).resolve().parent.parent
if str(_ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(_ENGINE_ROOT))

# Ensure sibling modules are importable
for _p in [_ENGINE_ROOT / "extraction_engine", _ENGINE_ROOT / "normalize"]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from extraction_record import ExtractionRecord, ExtractionResult
from normalized_record import (
    NormalizedRecord,
    NormalizationResult,
    NormalizationStatus,
)
from normalizers import normalize_record


# ── Canonical NORMALIZE version ───────────────────────────────────────

NORMALIZE_VERSION = "normalize-v1.0.0"


def _norm_config_hash() -> str:
    """Deterministic hash of normalize version + contract."""
    raw = f"normalizer={NORMALIZE_VERSION}:schema=v1"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ── Core normalization function ───────────────────────────────────────

def normalize_artifact(
    extraction_records: list[ExtractionRecord],
    artifact_id: str,
    artifact_path: Optional[str] = None,
) -> NormalizationResult:
    """Normalize all extraction records for one artifact.

    Each record is normalised independently. No merging or aggregation.
    Returns a NormalizationResult with per-status counts.
    """
    normalized: list[NormalizedRecord] = []
    errors: list[str] = []

    for rec in extraction_records:
        try:
            nrec = normalize_record(rec)
            normalized.append(nrec)
        except Exception as e:
            errors.append(f"error normalizing field '{rec.field_name}': {e}")
            normalized.append(
                NormalizedRecord(
                    artifact_id=rec.artifact_id,
                    source_type=rec.source_type,
                    source_identifier=rec.source_identifier,
                    source_uri=rec.source_uri,
                    original_field_name=rec.field_name,
                    verbatim_quote=rec.verbatim_quote,
                    source_location=rec.source_location,
                    content_hash=rec.content_hash,
                    extractor_version=rec.extractor_version,
                    extractor_config_hash=rec.extractor_config_hash,
                    field_type="unknown",
                    normalized_value=None,
                    raw_value=rec.extracted_value,
                    normalization_status=NormalizationStatus.UNSUPPORTED.value,
                    conflict_reason=str(e),
                )
            )

    total = len(normalized)
    norm_count = sum(1 for r in normalized
                     if r.normalization_status == NormalizationStatus.NORMALIZED.value)
    conflicts = sum(1 for r in normalized
                    if r.normalization_status == NormalizationStatus.CONFLICT.value)
    unsupported = sum(1 for r in normalized
                      if r.normalization_status == NormalizationStatus.UNSUPPORTED.value)
    skipped = sum(1 for r in normalized
                  if r.normalization_status == NormalizationStatus.SKIPPED.value)

    is_blocked = norm_count == 0 and total > 0
    err_msg = "; ".join(errors) if errors else ""
    if is_blocked:
        err_msg = f"BLOCKED: zero normalized records for artifact '{artifact_id}'"

    return NormalizationResult(
        artifact_id=artifact_id,
        records=tuple(normalized),
        total=total,
        normalized=norm_count,
        conflicts=conflicts,
        unsupported=unsupported,
        skipped=skipped,
        is_blocked=is_blocked,
        error_message=err_msg,
    )


# ── JSONL output ──────────────────────────────────────────────────────

DEFAULT_OUTPUT_DIR = str(_ENGINE_ROOT / "normalize" / "output")


def write_normalized_records(
    results: list[NormalizationResult],
    output_dir: Optional[str] = None,
) -> str:
    """Write normalized records to JSONL output file.

    Returns the output file path.
    """
    out_dir = output_dir or DEFAULT_OUTPUT_DIR
    os.makedirs(out_dir, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(out_dir, f"normalized_{ts}.jsonl")

    with open(out_path, "w", encoding="utf-8") as f:
        for result in results:
            for rec in result.records:
                f.write(json.dumps(rec.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")

    return out_path


# ── CLI entry point ───────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="P500-K NORMALIZE: normalize extraction records"
    )
    parser.add_argument("input", help="Path to extraction output JSONL file")
    parser.add_argument("--artifact-id", "-i", help="Artifact ID (default: auto-detect from records)")
    parser.add_argument("--output-dir", "-o", help="Output directory (default: normalize/output/)")
    args = parser.parse_args()

    if not os.path.isfile(args.input):
        print(f"ERROR: input not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    # Load extraction records
    records: list[ExtractionRecord] = []
    artifact_id = args.artifact_id or "unknown"
    with open(args.input, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            # Use first record's artifact_id if not specified
            if artifact_id == "unknown" and "artifact_id" in data:
                artifact_id = data["artifact_id"]
            records.append(ExtractionRecord(**data))

    if not records:
        print("ERROR: no extraction records loaded", file=sys.stderr)
        sys.exit(1)

    # Normalize
    result = normalize_artifact(records, artifact_id)

    # Write output
    out_path = write_normalized_records([result], args.output_dir)
    print(f"Normalized {result.total} records ({result.normalized} OK, "
          f"{result.conflicts} conflicts, {result.skipped} skipped, "
          f"{result.unsupported} unsupported)")
    print(f"Output: {out_path}")

    if result.is_blocked:
        print(f"WARNING: {result.error_message}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()


__all__ = [
    "normalize_artifact", "write_normalized_records",
    "NORMALIZE_VERSION", "_norm_config_hash",
]
