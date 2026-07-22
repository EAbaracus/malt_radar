"""Acquisition pipeline — canonical INGEST entry point (P500-H).

Usage:
    python -m mr-kep.acquisition.run_pipeline <source_path> --type <source_type>

Or programmatically:
    from mr_keq.acquisition.run_pipeline import run_ingest
    artifact = run_ingest("/path/to/file.csv", source_type="csv")
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Optional

# Canonical imports (absolute, to support both import and direct run)
_ACQ_ROOT = Path(__file__).resolve().parent
if str(_ACQ_ROOT) not in sys.path:
    sys.path.insert(0, str(_ACQ_ROOT))
from source_types import (
     SourceType, IngestRequest, IngestError,
 )
from artifact_store import ArtifactStore


def run_ingest(
    source_path: str,
    source_type: str,
    source_identifier: Optional[str] = None,
    source_uri: str = "",
    artifact_dir: Optional[str] = None,
    manifest_dir: Optional[str] = None,
) -> dict:
    """Acquire a single source artifact.

    Returns the SourceArtifact as a dict.

    Raises IngestError on failure.
    """
    if not os.path.exists(source_path):
        raise FileNotFoundError(f"source path does not exist: {source_path}")

    try:
        stype = SourceType(source_type.lower())
    except ValueError:
        raise ValueError(
            f"invalid source_type: {source_type!r}. "
            f"Valid: {', '.join(t.value for t in SourceType)}"
        )

    # Auto-detect identifier from filename if not given
    if not source_identifier:
        source_identifier = os.path.splitext(os.path.basename(source_path))[0]

    request = IngestRequest(
        source_type=stype,
        source_identifier=source_identifier,
        source_path=source_path,
        source_uri=source_uri or source_path,
    )

    store = ArtifactStore(
        artifact_dir=artifact_dir,
        manifest_dir=manifest_dir,
    )

    artifact = store.ingest(request)
    manifest_path = store.write_manifest()

    result = artifact.to_dict()
    result["manifest_path"] = manifest_path
    return result


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="MR-KEP Acquisition Pipeline (P500-H)"
    )
    parser.add_argument("source_path", help="Path to source file")
    parser.add_argument(
        "--type", "-t", dest="source_type",
        required=True,
        help=f"Source type ({', '.join(t.value for t in SourceType)})",
    )
    parser.add_argument(
        "--id", dest="source_identifier",
        default="",
        help="Source identifier (default: filename stem)",
    )
    parser.add_argument(
        "--uri", dest="source_uri",
        default="",
        help="Original source URI",
    )
    parser.add_argument(
        "--artifact-dir",
        default=None,
        help="Override artifact output directory",
    )
    parser.add_argument(
        "--manifest-dir",
        default=None,
        help="Override manifest output directory",
    )

    args = parser.parse_args(argv)

    try:
        result = run_ingest(
            source_path=args.source_path,
            source_type=args.source_type,
            source_identifier=args.source_id or None,
            source_uri=args.source_uri,
            artifact_dir=args.artifact_dir,
            manifest_dir=args.manifest_dir,
        )
    except (IngestError, FileNotFoundError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    print(f"Artifact ID:  {result['artifact_id']}")
    print(f"Source:       {result['source_identifier']}")
    print(f"SHA256:       {result['sha256']}")
    print(f"Size:         {result['byte_size']} bytes")
    print(f"Format:       {result['format']}")
    print(f"Status:       {result['status']}")
    print(f"Manifest:     {result.get('manifest_path', 'N/A')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
