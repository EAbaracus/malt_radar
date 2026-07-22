"""Acquisition artifact store (P500-H §2-3).

Immutable artifact storage with SHA256 identity, manifest generation,
and deterministic artifact IDs.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ── Canonical imports (absolute, to support both import and direct run)
import sys
_ACQ_ROOT = Path(__file__).resolve().parent
if str(_ACQ_ROOT) not in sys.path:
    sys.path.insert(0, str(_ACQ_ROOT))
from source_types import (
    SourceArtifact, SourceType, SourceFormat, IngestRequest,
    SourceMissingError, SourceUnreadableError, UnsupportedFormatError,
    DuplicateContentError, CorruptInputError, ZeroByteInputError,
    detect_format,
)

CANONICAL_ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
CANONICAL_MANIFEST_DIR = Path(__file__).resolve().parent / "manifests"


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(65536), b""):
            h.update(blk)
    return h.hexdigest()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _deterministic_artifact_id(sha256: str, source_id: str) -> str:
    """Deterministic artifact ID from content + identity (P500-H §2)."""
    raw = f"{sha256}:{source_id}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


class ArtifactStore:
    """Immutable, content-addressed artifact store.

    Every artifact stored at:
      artifacts/{artifact_id[:2]}/{artifact_id}.bin
    """

    def __init__(
        self,
        artifact_dir: Optional[str] = None,
        manifest_dir: Optional[str] = None,
    ):
        self._artifact_dir = Path(artifact_dir or CANONICAL_ARTIFACT_DIR)
        self._manifest_dir = Path(manifest_dir or CANONICAL_MANIFEST_DIR)
        self._artifact_dir.mkdir(parents=True, exist_ok=True)
        self._manifest_dir.mkdir(parents=True, exist_ok=True)
        self._manifest: list[SourceArtifact] = []
        self._seen_hashes: set[str] = set()

    # ── Public API ────────────────────────────────────────────────────

    def ingest(self, request: IngestRequest) -> SourceArtifact:
        """Acquire a single source artifact and store it immutably.

        Returns a SourceArtifact. Raises IngestError on failure.
        """
        source_path = Path(request.source_path)

        # Source missing
        if not source_path.exists():
            raise SourceMissingError(f"source not found: {source_path}")

        # Directory — not a valid artifact
        if source_path.is_dir():
            raise CorruptInputError(
                f"path is a directory, not a file: {source_path}"
            )

        # Zero-byte
        if source_path.stat().st_size == 0:
            raise ZeroByteInputError(f"zero-byte input: {source_path}")

        # Unreadable
        if not os.access(str(source_path), os.R_OK):
            raise SourceUnreadableError(f"source not readable: {source_path}")

        # Detect format
        fmt = detect_format(str(source_path))
        if fmt == SourceFormat.UNKNOWN and request.source_type in (
            SourceType.LOCAL_FILE, SourceType.CAPTURED_WEB,
        ):
            # Accept unknown format for web captures / generic files
            pass
        elif fmt == SourceFormat.UNKNOWN:
            raise UnsupportedFormatError(
                f"unsupported format: {source_path} "
                f"(extension not recognized)"
            )

        # SHA256
        try:
            sha = _sha256_file(str(source_path))
        except (IOError, OSError) as e:
            raise CorruptInputError(
                f"cannot hash source: {source_path}: {e}"
            )

        # Duplicate detection
        if sha in self._seen_hashes:
            artifact_id = _deterministic_artifact_id(sha, request.source_identifier)
            existing = self._find_artifact_by_hash(sha)
            if existing:
                dup_artifact = SourceArtifact(
                    artifact_id=artifact_id,
                    source_type=request.source_type,
                    source_identifier=request.source_identifier,
                    source_uri=request.source_uri,
                    sha256=sha,
                    byte_size=source_path.stat().st_size,
                    acquired_at=_now_iso(),
                    format=fmt,
                    filename=source_path.name,
                    status="duplicate",
                )
                self._manifest.append(dup_artifact)
                return dup_artifact
            raise DuplicateContentError(
                f"duplicate content hash: {sha[:16]}... "
                f"for source: {request.source_identifier}"
            )

        # Generate deterministic artifact ID
        artifact_id = _deterministic_artifact_id(sha, request.source_identifier)

        # Create shard directory
        shard = artifact_id[:2]
        dest_dir = self._artifact_dir / shard
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / f"{artifact_id}.bin"

        # Copy-immutable
        shutil.copy2(str(source_path), str(dest_path))

        # Build artifact metadata
        artifact = SourceArtifact(
            artifact_id=artifact_id,
            source_type=request.source_type,
            source_identifier=request.source_identifier,
            source_uri=request.source_uri,
            sha256=sha,
            byte_size=source_path.stat().st_size,
            acquired_at=_now_iso(),
            format=fmt,
            filename=source_path.name,
            status="acquired",
        )

        self._seen_hashes.add(sha)
        self._manifest.append(artifact)
        return artifact

    def write_manifest(self) -> str:
        """Flush current manifest to JSONL.

        Returns the manifest file path.
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        manifest_path = self._manifest_dir / f"manifest_{timestamp}.jsonl"

        records = [a.to_dict() for a in self._manifest]
        with open(str(manifest_path), "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
        return str(manifest_path)

    @property
    def artifact_count(self) -> int:
        return len([a for a in self._manifest if a.status == "acquired"])

    @property
    def duplicate_count(self) -> int:
        return len([a for a in self._manifest if a.status == "duplicate"])

    def _find_artifact_by_hash(self, sha: str) -> Optional[SourceArtifact]:
        for a in self._manifest:
            if a.sha256 == sha:
                return a
        return None

    def clear(self) -> None:
        """Clear in-memory state (does not delete stored artifacts)."""
        self._manifest.clear()
        self._seen_hashes.clear()


__all__ = ["ArtifactStore", "CANONICAL_ARTIFACT_DIR", "CANONICAL_MANIFEST_DIR"]
