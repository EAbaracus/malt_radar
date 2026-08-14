"""Extraction pipeline — canonical entry point (P500-I).

Usage:
    python -m mr-kep.extraction_engine.extractor <artifact_path> --artifact-id <id>

Or programmatically:
    from extraction_engine.extractor import run_extraction
    result = run_extraction("/path/artifact.bin", artifact_id="abc", source_type="csv")
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

# Canonical import path setup
_ENG_ROOT = Path(__file__).resolve().parent
if str(_ENG_ROOT) not in sys.path:
    sys.path.insert(0, str(_ENG_ROOT))

from extraction_record import (
    ExtractionResult, ExtractionError, _extractor_config_hash,
)
from extractors import extract_artifact, SourceMeta

OUTPUT_DIR = Path(__file__).resolve().parent / "output"


def _auto_source_type(path: str) -> str:
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    return {
        "csv": "csv",
        "json": "local_file",
        "jsonl": "local_file",
        "pdf": "pdf",
        "epub": "epub",
        "html": "captured_web",
        "htm": "captured_web",
        "txt": "local_file",
    }.get(ext, "local_file")


def run_extraction(
    artifact_path: str,
    artifact_id: str,
    source_type: str = "",
    source_identifier: str = "",
    source_uri: str = "",
    format_label: str = "",
    output_dir: Optional[str] = None,
) -> dict:
    """Extract structured fields from a raw P500-H artifact.

    Returns a dict with extraction result + output metadata.
    """
    if not source_type:
        source_type = _auto_source_type(artifact_path)
    if not source_identifier:
        source_identifier = os.path.splitext(os.path.basename(artifact_path))[0]

    meta = SourceMeta(
        artifact_id=artifact_id,
        source_type=source_type,
        source_identifier=source_identifier,
        source_uri=source_uri or artifact_path,
    )
    if not format_label:
        format_label = os.path.splitext(artifact_path)[1].lower().lstrip(".")

    result = extract_artifact(artifact_path, meta, format_label)

    # Write output JSONL
    out_dir = Path(output_dir or OUTPUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    artifact_slug = os.path.splitext(os.path.basename(artifact_path))[0]
    out_path = out_dir / f"{artifact_slug}_extraction.jsonl"

    with open(str(out_path), "w", encoding="utf-8") as f:
        for rec in result.records:
            f.write(json.dumps(rec.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")

    return {
        "artifact_id": result.artifact_id,
        "artifact_path": result.artifact_path,
        "output_path": str(out_path),
        "total_fields": result.total_fields,
        "successful_fields": result.successful_fields,
        "skipped_fields": result.skipped_fields,
        "failed_fields": result.failed_fields,
        "is_blocked": result.is_blocked,
        "extractor_config_hash": _extractor_config_hash(),
    }


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="MR-KEP Extraction Engine (P500-I)"
    )
    parser.add_argument("artifact_path", help="Path to raw acquisition artifact")
    parser.add_argument("--artifact-id", required=True, help="Artifact ID")
    parser.add_argument("--source-type", default="",
                        help="Source type override")
    parser.add_argument("--source-id", default="",
                        help="Source identifier (default: filename stem)")
    parser.add_argument("--source-uri", default="")
    parser.add_argument("--format", default="",
                        help="Format override (e.g. pdf)")
    parser.add_argument("--output-dir", default=None,
                        help="Override output directory")

    args = parser.parse_args(argv)

    if not os.path.isfile(args.artifact_path):
        print(f"ERROR: artifact not found: {args.artifact_path}", file=sys.stderr)
        return 1

    try:
        result = run_extraction(
            artifact_path=args.artifact_path,
            artifact_id=args.artifact_id,
            source_type=args.source_type,
            source_identifier=args.source_id or "",
            source_uri=args.source_uri or "",
            format_label=args.format or "",
            output_dir=args.output_dir,
        )
    except ExtractionError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    print(f"Artifact ID:   {result['artifact_id']}")
    print(f"Output:        {result['output_path']}")
    print(f"Fields:        {result['successful_fields']} extracted / "
          f"{result['skipped_fields']} skipped / "
          f"{result['failed_fields']} failed")
    print(f"Blocked:       {result['is_blocked']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
