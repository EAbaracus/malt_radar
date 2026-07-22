"""P500-H — Acquisition Pipeline Tests.

Tests: PDF, CSV, EPUB, web artifact fixtures, SHA256, deterministic ID,
manifest, duplicate, zero-byte, missing file, unsupported, corrupt,
immutability, production DB untouched.
"""

import hashlib
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest
import dataclasses
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent

sys.path.insert(0, str(ROOT / "mr-kep" / "acquisition"))

from source_types import (
    SourceType, SourceFormat, SourceArtifact, IngestRequest,
    SourceMissingError, SourceUnreadableError, UnsupportedFormatError,
    DuplicateContentError, CorruptInputError, ZeroByteInputError,
    detect_format,
)
from artifact_store import ArtifactStore, _sha256_file, _deterministic_artifact_id
from run_pipeline import run_ingest

FIXTURES = ROOT / "mr-kep" / "acquisition" / "tests" / "fixtures"
PRODUCTION_DB = str(ROOT / "output" / "import" / "production.db")

KNOWN_PROD_SHA = "e9ef4702189e6a36f7b5d4efc55124e60667e73491ae9ed55ba06040b3776783"


# Helper to create fixtures for formats that can't be written as plain text
def _create_pdf_fixture(path: str) -> str:
    """Write a minimal valid PDF (magic bytes only)."""
    # Minimal PDF header + one page
    content = (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>endobj\n"
        b"xref\n"
        b"0 4\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"trailer<</Size 4/Root 1 0 R>>\n"
        b"startxref\n"
        b"190\n"
        b"%%EOF\n"
    )
    with open(path, "wb") as f:
        f.write(content)
    return path


def _create_epub_fixture(path: str) -> str:
    """Write a minimal EPUB (ZIP with mimetype)."""
    import zipfile
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("mimetype", "application/epub+zip")
        zf.writestr("META-INF/container.xml", (
            '<?xml version="1.0"?><container version="1.0" '
            'xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
            '<rootfiles><rootfile full-path="content.opf" media-type="'
            'application/oebps-package+xml"/></rootfiles></container>'
        ))
        zf.writestr("content.opf", (
            '<?xml version="1.0"?><package version="3.0" '
            'xmlns="http://www.idpf.org/2007/opf">'
            '<metadata><dc:title xmlns:dc="http://purl.org/dc/elements/1.1/">'
            'Test</dc:title></metadata><spine/></package>'
        ))
        zf.writestr("OEBPS/test.xhtml", (
            '<html xmlns="http://www.w3.org/1999/xhtml"><body>'
            '<p>Test</p></body></html>'
        ))
    return path


# ═══════════════════════════════════════════════════════════════════════
# A. Source Type / Input Contract
# ═══════════════════════════════════════════════════════════════════════

class TestInputContract(unittest.TestCase):
    """A1. Input contract types and validation."""

    def test_source_type_enum(self):
        """SourceType enum has all expected values."""
        self.assertIn(SourceType.LOCAL_FILE, SourceType)
        self.assertIn(SourceType.PDF, SourceType)
        self.assertIn(SourceType.CSV, SourceType)
        self.assertIn(SourceType.EPUB, SourceType)
        self.assertIn(SourceType.CAPTURED_WEB, SourceType)

    def test_detect_format(self):
        """detect_format returns correct SourceFormat by extension."""
        self.assertEqual(detect_format("file.pdf"), SourceFormat.PDF)
        self.assertEqual(detect_format("file.csv"), SourceFormat.CSV)
        self.assertEqual(detect_format("file.epub"), SourceFormat.EPUB)
        self.assertEqual(detect_format("file.html"), SourceFormat.HTML)
        self.assertEqual(detect_format("file.JSON"), SourceFormat.JSON)
        self.assertEqual(detect_format("file.txt"), SourceFormat.TEXT)
        self.assertEqual(detect_format("file.xyz"), SourceFormat.UNKNOWN)

    def test_ingest_request_frozen(self):
        """IngestRequest is frozen (immutable)."""
        req = IngestRequest(
            source_type=SourceType.CSV,
            source_identifier="test-01",
            source_path="/tmp/test.csv",
        )
        with self.assertRaises(dataclasses.FrozenInstanceError):
            req.source_path = "/other"

    def test_source_artifact_to_dict(self):
        """SourceArtifact.to_dict() produces serializable output."""
        art = SourceArtifact(
            artifact_id="abc123",
            source_type=SourceType.CSV,
            source_identifier="test",
            source_uri="/tmp/test.csv",
            sha256="deadbeef",
            byte_size=100,
            acquired_at="2026-07-21T00:00:00",
            format=SourceFormat.CSV,
            filename="test.csv",
            status="acquired",
        )
        d = art.to_dict()
        self.assertEqual(d["artifact_id"], "abc123")
        self.assertEqual(d["format"], "text/csv")
        self.assertEqual(d["status"], "acquired")


# ═══════════════════════════════════════════════════════════════════════
# B. Artifact Store — Ingestion
# ═══════════════════════════════════════════════════════════════════════

class TestArtifactStore(unittest.TestCase):
    """B. Real ingestion of supported source types."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="p500h_")
        self.store = ArtifactStore(
            artifact_dir=os.path.join(self.tmpdir, "artifacts"),
            manifest_dir=os.path.join(self.tmpdir, "manifests"),
        )

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _ingest_fixture(self, fixture_name: str, source_type: str, identifier: str = ""):
        path = str(FIXTURES / fixture_name)
        if not os.path.exists(path):
            self.skipTest(f"fixture not found: {path}")
        return self.store.ingest(IngestRequest(
            source_type=SourceType(source_type),
            source_identifier=identifier or os.path.splitext(fixture_name)[0],
            source_path=path,
        ))

    def test_ingest_csv(self):
        """CSV fixture acquires successfully."""
        art = self._ingest_fixture("fixture_valid.csv", "csv")
        self.assertEqual(art.status, "acquired")
        self.assertGreater(art.byte_size, 0)
        self.assertEqual(art.format, SourceFormat.CSV)
        self.assertNotEqual(art.sha256, "")

    def test_ingest_json(self):
        """JSON fixture acquires successfully."""
        art = self._ingest_fixture("fixture_valid.json", "local_file")
        self.assertEqual(art.status, "acquired")
        self.assertEqual(art.format, SourceFormat.JSON)

    def test_ingest_pdf(self):
        """PDF fixture acquires successfully."""
        pdf_path = os.path.join(self.tmpdir, "fixture_valid.pdf")
        _create_pdf_fixture(pdf_path)
        art = self.store.ingest(IngestRequest(
            source_type=SourceType.PDF,
            source_identifier="test-pdf",
            source_path=pdf_path,
        ))
        self.assertEqual(art.status, "acquired")
        self.assertEqual(art.format, SourceFormat.PDF)

    def test_ingest_epub(self):
        """EPUB fixture acquires successfully."""
        epub_path = os.path.join(self.tmpdir, "fixture_valid.epub")
        _create_epub_fixture(epub_path)
        art = self.store.ingest(IngestRequest(
            source_type=SourceType.EPUB,
            source_identifier="test-epub",
            source_path=epub_path,
        ))
        self.assertEqual(art.status, "acquired")
        self.assertEqual(art.format, SourceFormat.EPUB)

    def test_ingest_web_artifact(self):
        """Captured web artifact (HTML) acquires successfully."""
        html_path = os.path.join(self.tmpdir, "fixture_web.html")
        with open(html_path, "w") as f:
            f.write("<html><body><h1>Test Whisky Review</h1></body></html>")
        art = self.store.ingest(IngestRequest(
            source_type=SourceType.CAPTURED_WEB,
            source_identifier="test-web",
            source_path=html_path,
            source_uri="https://example.com/whisky-review",
        ))
        self.assertEqual(art.status, "acquired")
        self.assertEqual(art.format, SourceFormat.HTML)
        self.assertIn("example.com", art.source_uri)

    def test_sha256_not_empty(self):
        """Acquired artifact has non-empty SHA256."""
        art = self._ingest_fixture("fixture_valid.csv", "csv")
        self.assertNotEqual(art.sha256, "")
        self.assertEqual(len(art.sha256), 64)

    def test_deterministic_artifact_id(self):
        """Same content + identifier produces same artifact ID."""
        art1 = self._ingest_fixture("fixture_valid.csv", "csv", "dup-test")
        art2 = self._ingest_fixture("fixture_valid.csv", "csv", "dup-test")
        # Second one is detected as duplicate
        self.assertEqual(art2.artifact_id, art1.artifact_id)

    def test_different_content_different_id(self):
        """Different contents produce different IDs (even same filename)."""
        art1 = self._ingest_fixture("fixture_valid.csv", "csv")
        art2 = self._ingest_fixture("fixture_valid.json", "local_file")
        self.assertNotEqual(art1.artifact_id, art2.artifact_id)


# ═══════════════════════════════════════════════════════════════════════
# C. Manifest
# ═══════════════════════════════════════════════════════════════════════

class TestManifest(unittest.TestCase):
    """C. Manifest generation."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="p500h_")
        self.store = ArtifactStore(
            artifact_dir=os.path.join(self.tmpdir, "artifacts"),
            manifest_dir=os.path.join(self.tmpdir, "manifests"),
        )

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_write_manifest_creates_file(self):
        """write_manifest() creates JSONL file."""
        path = str(FIXTURES / "fixture_valid.csv")
        self.store.ingest(IngestRequest(SourceType.CSV, "csv-manifest", path))
        manifest_path = self.store.write_manifest()
        self.assertTrue(os.path.exists(manifest_path))
        with open(manifest_path) as f:
            lines = f.readlines()
        self.assertGreater(len(lines), 0)
        record = json.loads(lines[0])
        self.assertIn("artifact_id", record)
        self.assertIn("sha256", record)
        self.assertIn("status", record)

    def test_manifest_records_all_acquisitions(self):
        """Manifest contains all ingested artifacts."""
        csv_path = str(FIXTURES / "fixture_valid.csv")
        json_path = str(FIXTURES / "fixture_valid.json")
        self.store.ingest(IngestRequest(SourceType.CSV, "m1", csv_path))
        self.store.ingest(IngestRequest(SourceType.LOCAL_FILE, "m2", json_path))
        manifest_path = self.store.write_manifest()
        with open(manifest_path) as f:
            records = [json.loads(line) for line in f]
        self.assertEqual(len(records), 2)
        self.assertEqual({r["source_identifier"] for r in records}, {"m1", "m2"})

    def test_manifest_deterministic_fields(self):
        """SHA256 and byte_size are deterministic."""
        path = str(FIXTURES / "fixture_valid.csv")
        self.store.ingest(IngestRequest(SourceType.CSV, "det", path))
        m1 = self.store.write_manifest()
        self.store.clear()
        self.store.ingest(IngestRequest(SourceType.CSV, "det", path))
        m2 = self.store.write_manifest()
        with open(m1) as f:
            r1 = json.loads(f.readline())
        with open(m2) as f:
            r2 = json.loads(f.readline())
        self.assertEqual(r1["sha256"], r2["sha256"])
        self.assertEqual(r1["byte_size"], r2["byte_size"])
        self.assertEqual(r1["artifact_id"], r2["artifact_id"])


# ═══════════════════════════════════════════════════════════════════════
# D. Deduplication
# ═══════════════════════════════════════════════════════════════════════

class TestDeduplication(unittest.TestCase):
    """D. SHA256-based content identity."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="p500h_")
        self.store = ArtifactStore(
            artifact_dir=os.path.join(self.tmpdir, "artifacts"),
            manifest_dir=os.path.join(self.tmpdir, "manifests"),
        )

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_duplicate_hash_returns_duplicate_status(self):
        """Same content → status='duplicate', not re-stored."""
        path = str(FIXTURES / "fixture_valid.csv")
        a1 = self.store.ingest(IngestRequest(SourceType.CSV, "dup-test", path))
        a2 = self.store.ingest(IngestRequest(SourceType.CSV, "dup-test", path))
        self.assertEqual(a1.status, "acquired")
        self.assertEqual(a2.status, "duplicate")

    def test_different_content_same_filename_distinct(self):
        """Different hashes with same filename remain distinct."""
        path1 = str(FIXTURES / "fixture_valid.csv")
        path2 = str(FIXTURES / "fixture_valid.json")
        a1 = self.store.ingest(IngestRequest(SourceType.CSV, "same-name", path1))
        a2 = self.store.ingest(IngestRequest(SourceType.LOCAL_FILE, "same-name", path2))
        self.assertEqual(a1.status, "acquired")
        self.assertEqual(a2.status, "acquired")
        self.assertNotEqual(a1.sha256, a2.sha256)

    def test_duplicate_not_counted_twice(self):
        """artifact_count excludes duplicates."""
        path = str(FIXTURES / "fixture_valid.csv")
        self.store.ingest(IngestRequest(SourceType.CSV, "cnt", path))
        self.assertEqual(self.store.artifact_count, 1)
        self.store.ingest(IngestRequest(SourceType.CSV, "cnt", path))
        self.assertEqual(self.store.artifact_count, 1)
        self.assertEqual(self.store.duplicate_count, 1)


# ═══════════════════════════════════════════════════════════════════════
# E. Failure Modes
# ═══════════════════════════════════════════════════════════════════════

class TestFailureModes(unittest.TestCase):
    """E. All failure modes close cleanly."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="p500h_")
        self.store = ArtifactStore(
            artifact_dir=os.path.join(self.tmpdir, "artifacts"),
            manifest_dir=os.path.join(self.tmpdir, "manifests"),
        )

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_missing_file_rejected(self):
        """Missing source file raises SourceMissingError."""
        missing = os.path.join(self.tmpdir, "nonexistent.csv")
        with self.assertRaises(SourceMissingError):
            self.store.ingest(IngestRequest(
                SourceType.CSV, "missing", missing,
            ))

    def test_zero_byte_file_rejected(self):
        """Zero-byte file raises ZeroByteInputError."""
        zero_path = os.path.join(self.tmpdir, "empty.txt")
        with open(zero_path, "w") as f:
            pass
        with self.assertRaises(ZeroByteInputError):
            self.store.ingest(IngestRequest(
                SourceType.LOCAL_FILE, "zero", zero_path,
            ))

    def test_unsupported_format_rejected(self):
        """Unknown extension raises UnsupportedFormatError for typed sources."""
        with open(os.path.join(self.tmpdir, "test.xyz"), "w") as f:
            f.write("some content")
        with self.assertRaises(UnsupportedFormatError):
            self.store.ingest(IngestRequest(
                SourceType.PDF, "unsupported",
                os.path.join(self.tmpdir, "test.xyz"),
            ))

    def test_corrupt_input_rejected(self):
        """Unreadable content raises CorruptInputError."""
        # On Windows we can't easily make a file disappear between
        # existence-check and read, but we can test by passing a directory
        dir_path = os.path.join(self.tmpdir, "not_a_file")
        os.makedirs(dir_path, exist_ok=True)
        with self.assertRaises((IsADirectoryError, CorruptInputError)):
            self.store.ingest(IngestRequest(
                SourceType.CSV, "corrupt", dir_path,
            ))


# ═══════════════════════════════════════════════════════════════════════
# F. Immutability
# ═══════════════════════════════════════════════════════════════════════

class TestImmutability(unittest.TestCase):
    """F. Stored artifacts are immutable."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="p500h_")
        self.store = ArtifactStore(
            artifact_dir=os.path.join(self.tmpdir, "artifacts"),
            manifest_dir=os.path.join(self.tmpdir, "manifests"),
        )

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_artifact_file_not_overwritten(self):
        """Same content not stored twice — duplicate status."""
        path = str(FIXTURES / "fixture_valid.csv")
        a1 = self.store.ingest(IngestRequest(SourceType.CSV, "imm", path))
        a2 = self.store.ingest(IngestRequest(SourceType.CSV, "imm", path))
        self.assertEqual(a2.status, "duplicate")

    def test_sha256_matches_stored_content(self):
        """Artifact on disk SHA matches manifest."""
        path = str(FIXTURES / "fixture_valid.csv")
        a1 = self.store.ingest(IngestRequest(SourceType.CSV, "sha", path))
        shard = a1.artifact_id[:2]
        stored_path = os.path.join(
            self.tmpdir, "artifacts", shard, f"{a1.artifact_id}.bin"
        )
        self.assertTrue(os.path.exists(stored_path))
        disk_sha = _sha256_file(stored_path)
        self.assertEqual(disk_sha, a1.sha256)


# ═══════════════════════════════════════════════════════════════════════
# G. Production DB immutability
# ═══════════════════════════════════════════════════════════════════════

class TestProductionImmutability(unittest.TestCase):
    """G. Production DB unchanged after all tests."""

    def test_production_db_sha(self):
        """Production DB SHA matches known value."""
        sha = _sha256_file(PRODUCTION_DB)
        self.assertEqual(sha, KNOWN_PROD_SHA)

    def test_production_db_counts(self):
        """Production DB row counts unchanged."""
        c = sqlite3.connect(f"file:{PRODUCTION_DB}?mode=ro", uri=True)
        tables = c.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
        ).fetchone()[0]
        whisky = c.execute("SELECT COUNT(*) FROM whiskies").fetchone()[0]
        fe = c.execute("SELECT COUNT(*) FROM flavor_evidence").fetchone()[0]
        c.close()
        self.assertEqual(tables, 37)
        self.assertEqual(whisky, 4749)
        self.assertEqual(fe, 2881)


# ═══════════════════════════════════════════════════════════════════════
# H. run_pipeline entry point
# ═══════════════════════════════════════════════════════════════════════

class TestRunPipeline(unittest.TestCase):
    """H. run_ingest() entry point."""

    def test_run_ingest_csv(self):
        """run_ingest works with CSV."""
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = str(FIXTURES / "fixture_valid.csv")
            result = run_ingest(
                source_path=csv_path,
                source_type="csv",
                source_identifier="run-test",
                artifact_dir=os.path.join(tmp, "artifacts"),
                manifest_dir=os.path.join(tmp, "manifests"),
            )
            self.assertEqual(result["status"], "acquired")
            self.assertIn("manifest_path", result)

    def test_run_ingest_missing_file(self):
        """run_ingest raises FileNotFoundError for missing source."""
        with self.assertRaises(FileNotFoundError):
            run_ingest(
                source_path="/nonexistent/path.csv",
                source_type="csv",
            )

    def test_run_ingest_invalid_type(self):
        """run_ingest raises ValueError for invalid source_type."""
        with self.assertRaises(ValueError):
            run_ingest(
                source_path=str(FIXTURES / "fixture_valid.csv"),
                source_type="spaceship",
            )


if __name__ == "__main__":
    unittest.main()
