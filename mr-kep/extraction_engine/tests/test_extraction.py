"""P500-I — Extraction Pipeline Tests.

Tests: PDF, CSV, EPUB, HTML extraction; structured fields, verbatim quotes,
source provenance, determinism, failure modes, raw artifact immutability,
production DB untouched.
"""

import hashlib
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent  # → repo root

_ENGINE = str(ROOT / "mr-kep" / "extraction_engine")
sys.path.insert(0, _ENGINE)

from extraction_record import (
    ExtractionRecord, ExtractionResult, ExtractionStatus,
    ExtractorVersion, _extractor_config_hash,
    ExtractionError, MissingArtifactError, UnsupportedFormatError,
    CorruptArtifactError, ZeroFieldsError,
)
from extractors import (
    extract_artifact, SourceMeta,
    CsvExtractor, JsonExtractor, HtmlExtractor,
    PdfExtractor, EpubExtractor,
)
from extractor import run_extraction

FIXTURES = ROOT / "mr-kep" / "extraction_engine" / "tests" / "fixtures"
PRODUCTION_DB = str(ROOT / "output" / "import" / "production.db")

KNOWN_PROD_SHA = "e9ef4702189e6a36f7b5d4efc55124e60667e73491ae9ed55ba06040b3776783"


# ── Fixture helpers ───────────────────────────────────────────────────

def _make_pdf(path: str) -> str:
    content = (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]"
        b"/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
        b"4 0 obj<</Length 44>>stream\n"
        b"BT /F1 12 Tf 100 700 Td (Ardbeg 10 Year) Tj ET\n"
        b"endstream\nendobj\n"
        b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
        b"xref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n"
        b"0000000058 00000 n \n0000000115 00000 n \n0000000266 00000 n \n"
        b"0000000350 00000 n \ntrailer<</Size 6/Root 1 0 R>>\n"
        b"startxref\n418\n%%EOF\n"
    )
    with open(path, "wb") as f:
        f.write(content)
    return path


def _make_epub(path: str) -> str:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("mimetype", "application/epub+zip")
        zf.writestr("META-INF/container.xml",
            '<?xml version="1.0"?><container version="1.0" '
            'xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
            '<rootfiles><rootfile full-path="content.opf" media-type='
            '"application/oebps-package+xml"/></rootfiles></container>'
        )
        zf.writestr("content.opf",
            '<?xml version="1.0"?><package version="3.0" '
            'xmlns="http://www.idpf.org/2007/opf">'
            '<metadata><dc:title xmlns:dc="http://purl.org/dc/elements/1.1/">'
            'Whisky Tasting Notes</dc:title>'
            '<dc:creator xmlns:dc="http://purl.org/dc/elements/1.1/">'
            'Test Author</dc:creator></metadata>'
            '<manifest><item id="chapter1" href="OEBPS/chapter1.xhtml" '
            'media-type="application/xhtml+xml"/></manifest>'
            '<spine><itemref idref="chapter1"/></spine>'
            '<guide/></package>'
        )
        zf.writestr("OEBPS/chapter1.xhtml",
            '<html xmlns="http://www.w3.org/1999/xhtml">'
            '<head><title>Chapter 1</title></head>'
            '<body><p>Ardbeg 10 Year Old is a classic Islay single malt.</p>'
            '<p>The nose offers powerful peat smoke with citrus notes.</p>'
            '</body></html>'
        )
    return path


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(65536), b""):
            h.update(blk)
    return h.hexdigest()


# ═══════════════════════════════════════════════════════════════════════
# A. ExtractionRecord contract
# ═══════════════════════════════════════════════════════════════════════

class TestExtractionRecord(unittest.TestCase):
    """A. ExtractionRecord schema and behavior."""

    def test_record_frozen(self):
        """ExtractionRecord is immutable."""
        r = ExtractionRecord(
            artifact_id="a1", source_type="csv",
            source_identifier="s1", source_uri="/tmp/x.csv",
            field_name="csv:name", extracted_value="Ardbeg",
            verbatim_quote="Ardbeg", source_location="row:1",
            content_hash="abc", extraction_status="extracted",
        )
        with self.assertRaises(Exception):
            r.field_name = "other"

    def test_record_to_dict_all_fields(self):
        """to_dict() contains all required fields."""
        r = ExtractionRecord(
            artifact_id="a1", source_type="csv",
            source_identifier="s1", source_uri="/tmp/x.csv",
            field_name="csv:name", extracted_value="Ardbeg",
            verbatim_quote="Ardbeg", source_location="row:1",
            content_hash="abc", extraction_status="extracted",
        )
        d = r.to_dict()
        for k in ("artifact_id", "source_type", "field_name",
                  "extracted_value", "verbatim_quote", "content_hash",
                  "extraction_status", "extractor_version",
                  "extractor_config_hash"):
            self.assertIn(k, d)

    def test_extractor_config_hash_populated(self):
        """extractor_config_hash is auto-populated."""
        r = ExtractionRecord(
            artifact_id="a1", source_type="csv",
            source_identifier="s1", source_uri="/tmp/x.csv",
            field_name="csv:name", extracted_value="Ardbeg",
            verbatim_quote="Ardbeg", source_location="row:1",
            content_hash="abc", extraction_status="extracted",
        )
        self.assertNotEqual(r.extractor_config_hash, "")
        self.assertEqual(len(r.extractor_config_hash), 16)

    def test_extractor_config_hash_deterministic(self):
        """Same extractor version → same config hash."""
        h1 = _extractor_config_hash()
        h2 = _extractor_config_hash()
        self.assertEqual(h1, h2)


# ═══════════════════════════════════════════════════════════════════════
# B. CSV Extraction
# ═══════════════════════════════════════════════════════════════════════

class TestCsvExtraction(unittest.TestCase):
    """B. CSV extraction with real parser."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="p500i_")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _extract(self, path: str) -> ExtractionResult:
        meta = SourceMeta("csv-test", "csv", "sample_whisky", path)
        ext = CsvExtractor()
        return ext.extract(str(path), meta)

    def test_csv_extracts_all_rows(self):
        """CSV extractor produces records for every row."""
        path = FIXTURES / "sample_whisky.csv"
        result = self._extract(path)
        self.assertGreater(result.successful_fields, 0)
        # 4 rows × 5 fields = 20 (but header row is skip, empty vals skip)
        self.assertGreater(result.total_fields, 10)

    def test_csv_verbatim_quote_originates_from_file(self):
        """Verbatim quotes match actual file content."""
        path = FIXTURES / "sample_whisky.csv"
        result = self._extract(path)
        # Check a known value
        for rec in result.records:
            if rec.field_name == "csv:whisky":
                self.assertIn("Ardbeg", rec.verbatim_quote)
                break
        else:
            self.fail("no csv:whisky field found")

    def test_csv_source_location_has_row_number(self):
        """CSV records include row number as source_location."""
        path = FIXTURES / "sample_whisky.csv"
        result = self._extract(path)
        rows = set()
        for rec in result.records:
            rows.add(rec.source_location)
        # At least row:1, row:2, row:3, row:4
        self.assertGreaterEqual(len(rows), 4)

    def test_csv_content_hash_matches_file(self):
        """content_hash == SHA256 of the raw artifact."""
        path = FIXTURES / "sample_whisky.csv"
        result = self._extract(path)
        known_sha = _sha256(str(path))
        for rec in result.records:
            self.assertEqual(rec.content_hash, known_sha)

    def test_csv_not_blocked(self):
        """Successful CSV extraction is not blocked."""
        path = FIXTURES / "sample_whisky.csv"
        result = self._extract(path)
        self.assertFalse(result.is_blocked)

    def test_csv_empty_file(self):
        """Empty CSV produces zero fields (not blocked because 0 total)."""
        empty = os.path.join(self.tmpdir, "empty.csv")
        with open(empty, "w") as f:
            f.write("col1,col2\n")  # header only, no data rows
        result = self._extract(empty)
        self.assertEqual(result.total_fields, 0)


# ═══════════════════════════════════════════════════════════════════════
# C. JSON Extraction
# ═══════════════════════════════════════════════════════════════════════

class TestJsonExtraction(unittest.TestCase):
    """C. JSON extraction."""

    def _extract(self, path: str) -> ExtractionResult:
        meta = SourceMeta("json-test", "local_file", "sample_whisky", str(path))
        ext = JsonExtractor()
        return ext.extract(str(path), meta)

    def test_json_extracts_string_and_numeric_fields(self):
        """JSON extractor handles strings and numbers."""
        path = FIXTURES / "sample_whisky.json"
        result = self._extract(path)
        fields = {r.field_name: r.extracted_value for r in result.records}
        self.assertIn("whisky", fields)
        self.assertIn("distillery", fields)
        self.assertIn("rating", fields)
        self.assertEqual(fields["rating"], "88")

    def test_json_verbatim_quote(self):
        """Verbatim quote matches source JSON."""
        path = FIXTURES / "sample_whisky.json"
        result = self._extract(path)
        for rec in result.records:
            if rec.field_name == "whisky":
                self.assertEqual(rec.verbatim_quote, "Ardbeg 10 Year Old")
                return
        self.fail("no whisky field")

    def test_json_nested_source(self):
        """JSON nested fields use dot notation."""
        path = FIXTURES / "sample_whisky.json"
        result = self._extract(path)
        field_names = {r.field_name for r in result.records}
        self.assertIn("source.name", field_names)
        self.assertIn("source.issue", field_names)


# ═══════════════════════════════════════════════════════════════════════
# D. HTML / Captured Web Artifact Extraction
# ═══════════════════════════════════════════════════════════════════════

class TestHtmlExtraction(unittest.TestCase):
    """D. HTML/captured web artifact extraction."""

    def _extract(self, path: str) -> ExtractionResult:
        meta = SourceMeta("html-test", "captured_web", "sample_web", str(path))
        ext = HtmlExtractor()
        return ext.extract(str(path), meta)

    def test_html_extracts_title(self):
        """HTML title is extracted."""
        path = FIXTURES / "sample_web_artifact.html"
        result = self._extract(path)
        field_names = {r.field_name: r.extracted_value for r in result.records}
        self.assertIn("html:title", field_names)
        self.assertIn("Ardbeg", field_names["html:title"])

    def test_html_extracts_meta_description(self):
        """HTML meta description is extracted."""
        path = FIXTURES / "sample_web_artifact.html"
        result = self._extract(path)
        field_names = {r.field_name: r.extracted_value for r in result.records}
        self.assertIn("html:meta_description", field_names)
        self.assertIn("peat smoke", field_names["html:meta_description"])

    def test_html_extracts_h1(self):
        """HTML h1 heading is extracted."""
        path = FIXTURES / "sample_web_artifact.html"
        result = self._extract(path)
        field_names = {r.field_name: r.extracted_value for r in result.records}
        self.assertTrue(any(k.startswith("html:h1") for k in field_names))

    def test_html_extracts_paragraphs(self):
        """HTML paragraphs are extracted."""
        path = FIXTURES / "sample_web_artifact.html"
        result = self._extract(path)
        self.assertGreater(result.successful_fields, 3)  # title + meta + h1 + p

    def test_html_content_hash(self):
        """content_hash matches source file."""
        path = FIXTURES / "sample_web_artifact.html"
        result = self._extract(path)
        known_sha = _sha256(str(path))
        for rec in result.records:
            self.assertEqual(rec.content_hash, known_sha)

    def test_html_not_blocked(self):
        """Successful HTML extraction is not blocked."""
        path = FIXTURES / "sample_web_artifact.html"
        result = self._extract(path)
        self.assertFalse(result.is_blocked)

    def test_html_verbatim_quote_from_artifact(self):
        """Verbatim quote originates in the raw HTML."""
        path = FIXTURES / "sample_web_artifact.html"
        result = self._extract(path)
        for rec in result.records:
            if rec.field_name == "html:title":
                self.assertIn("Ardbeg", rec.verbatim_quote)
                return
        self.fail("no html:title field")


# ═══════════════════════════════════════════════════════════════════════
# E. PDF Extraction
# ═══════════════════════════════════════════════════════════════════════

class TestPdfExtraction(unittest.TestCase):
    """E. PDF extraction using pdfminer."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="p500i_")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_pdf_extraction(self):
        """PDF extractor produces page records."""
        pdf_path = os.path.join(self.tmpdir, "test_whisky.pdf")
        _make_pdf(pdf_path)
        meta = SourceMeta("pdf-test", "pdf", "sample_pdf", pdf_path)
        ext = PdfExtractor()
        result = ext.extract(pdf_path, meta)
        self.assertGreater(result.successful_fields, 0)
        self.assertFalse(result.is_blocked)

    def test_pdf_verbatim_quote_contains_page_text(self):
        """Verbatim quote from PDF contains text from the PDF."""
        pdf_path = os.path.join(self.tmpdir, "test_whisky.pdf")
        _make_pdf(pdf_path)
        meta = SourceMeta("pdf-test", "pdf", "sample_pdf", pdf_path)
        ext = PdfExtractor()
        result = ext.extract(pdf_path, meta)
        for rec in result.records:
            if rec.field_name.startswith("pdf:page"):
                self.assertIn("Ardbeg", rec.verbatim_quote)
                return
        self.fail("no pdf:page field found")

    def test_pdf_content_hash(self):
        """content_hash matches PDF file."""
        pdf_path = os.path.join(self.tmpdir, "test_whisky.pdf")
        _make_pdf(pdf_path)
        known_sha = _sha256(pdf_path)
        meta = SourceMeta("pdf-test", "pdf", "sample_pdf", pdf_path)
        ext = PdfExtractor()
        result = ext.extract(pdf_path, meta)
        for rec in result.records:
            self.assertEqual(rec.content_hash, known_sha)


# ═══════════════════════════════════════════════════════════════════════
# F. EPUB Extraction
# ═══════════════════════════════════════════════════════════════════════

class TestEpubExtraction(unittest.TestCase):
    """F. EPUB extraction using ebooklib."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="p500i_")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_epub_extracts_title_and_creator(self):
        """EPUB metadata fields are extracted."""
        epub_path = os.path.join(self.tmpdir, "test_whisky.epub")
        _make_epub(epub_path)
        meta = SourceMeta("epub-test", "epub", "sample_epub", epub_path)
        ext = EpubExtractor()
        result = ext.extract(epub_path, meta)
        field_names = {r.field_name: r.extracted_value for r in result.records}
        self.assertIn("epub:title", field_names)
        self.assertIn("epub:creator", field_names)

    def test_epub_document_content(self):
        """EPUB document items produce records."""
        epub_path = os.path.join(self.tmpdir, "test_whisky.epub")
        _make_epub(epub_path)
        meta = SourceMeta("epub-test", "epub", "sample_epub", epub_path)
        ext = EpubExtractor()
        result = ext.extract(epub_path, meta)
        self.assertGreater(result.successful_fields, 2)  # title + creator + doc

    def test_epub_not_blocked(self):
        """Successful EPUB extraction is not blocked."""
        epub_path = os.path.join(self.tmpdir, "test_whisky.epub")
        _make_epub(epub_path)
        meta = SourceMeta("epub-test", "epub", "sample_epub", epub_path)
        ext = EpubExtractor()
        result = ext.extract(epub_path, meta)
        self.assertFalse(result.is_blocked)


# ═══════════════════════════════════════════════════════════════════════
# G. Determinism
# ═══════════════════════════════════════════════════════════════════════

class TestDeterminism(unittest.TestCase):
    """G. Same input → same output."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="p500i_")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_csv_deterministic_extraction(self):
        """Same CSV → identical extraction records."""
        path = str(FIXTURES / "sample_whisky.csv")
        meta = SourceMeta("det-csv", "csv", "sample", path)
        ext = CsvExtractor()
        r1 = ext.extract(path, meta)
        r2 = ext.extract(path, meta)
        self.assertEqual(
            [r.to_dict() for r in r1.records],
            [r.to_dict() for r in r2.records],
        )

    def test_json_deterministic_extraction(self):
        """Same JSON → identical extraction records."""
        path = str(FIXTURES / "sample_whisky.json")
        meta = SourceMeta("det-json", "local_file", "sample", path)
        ext = JsonExtractor()
        r1 = ext.extract(path, meta)
        r2 = ext.extract(path, meta)
        self.assertEqual(len(r1.records), len(r2.records))
        for rd1, rd2 in zip(r1.records, r2.records):
            self.assertEqual(rd1.field_name, rd2.field_name)
            self.assertEqual(rd1.extracted_value, rd2.extracted_value)
            self.assertEqual(rd1.verbatim_quote, rd2.verbatim_quote)


# ═══════════════════════════════════════════════════════════════════════
# H. Failure Modes
# ═══════════════════════════════════════════════════════════════════════

class TestFailureModes(unittest.TestCase):
    """H. All failure modes close cleanly."""

    def test_missing_artifact(self):
        """Missing artifact raises MissingArtifactError."""
        with self.assertRaises(MissingArtifactError):
            extract_artifact(
                "/nonexistent/path.csv",
                SourceMeta("m1", "csv", "missing", ""),
            )

    def test_unsupported_format(self):
        """Unknown format raises UnsupportedFormatError."""
        path = str(FIXTURES / "sample_unsupported.xyz")
        with self.assertRaises(UnsupportedFormatError):
            extract_artifact(
                path,
                SourceMeta("m2", "local_file", "unsupported", ""),
            )

    def test_zero_fields_still_returns_result(self):
        """Extraction with zero fields returns blocked=False + 0 fields."""
        # Empty CSV with only header → 0 records (no data rows)
        tmpdir = tempfile.mkdtemp(prefix="p500i_")
        try:
            empty = os.path.join(tmpdir, "header_only.csv")
            with open(empty, "w") as f:
                f.write("col1,col2\n")
            meta = SourceMeta("m3", "csv", "empty", empty)
            ext = CsvExtractor()
            result = ext.extract(empty, meta)
            self.assertEqual(result.total_fields, 0)
            # ZeroFieldsError is raised by extract_artifact() only when
            # successful_fields==0 AND total_fields > 0
            self.assertEqual(result.successful_fields, 0)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_extract_artifact_wraps_zero_fields_with_blocked_true(self):
        """extract_artifact raises ZeroFieldsError when all fail."""
        tmpdir = tempfile.mkdtemp(prefix="p500i_")
        try:
            # A CSV with header but no data → check
            empty = os.path.join(tmpdir, "nope.csv")
            with open(empty, "w") as f:
                f.write("col1,col2\n")  # header only
            with self.assertRaises(ZeroFieldsError):
                extract_artifact(
                    empty,
                    SourceMeta("m4", "csv", "empty", ""),
                )
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


# ═══════════════════════════════════════════════════════════════════════
# I. Raw Artifact Immutability
# ═══════════════════════════════════════════════════════════════════════

class TestImmutability(unittest.TestCase):
    """I. Extraction never modifies raw artifacts."""

    def test_extract_does_not_modify_csv(self):
        """CSV file content SHA unchanged after extraction."""
        path = str(FIXTURES / "sample_whisky.csv")
        sha_before = _sha256(path)
        meta = SourceMeta("imm-csv", "csv", "sample", path)
        ext = CsvExtractor()
        ext.extract(path, meta)
        self.assertEqual(sha_before, _sha256(path))

    def test_extract_does_not_modify_html(self):
        """HTML file content SHA unchanged after extraction."""
        path = str(FIXTURES / "sample_web_artifact.html")
        sha_before = _sha256(path)
        meta = SourceMeta("imm-html", "captured_web", "sample", path)
        ext = HtmlExtractor()
        ext.extract(path, meta)
        self.assertEqual(sha_before, _sha256(path))


# ═══════════════════════════════════════════════════════════════════════
# J. run_extraction entry point
# ═══════════════════════════════════════════════════════════════════════

class TestRunExtraction(unittest.TestCase):
    """J. run_extraction() entry point."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="p500i_")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_run_extraction_csv(self):
        """run_extraction produces JSONL output file."""
        csv_path = str(FIXTURES / "sample_whisky.csv")
        result = run_extraction(
            artifact_path=csv_path,
            artifact_id="run-test",
            source_type="csv",
            output_dir=os.path.join(self.tmpdir, "out"),
        )
        self.assertGreater(result["successful_fields"], 0)
        self.assertTrue(os.path.exists(result["output_path"]))
        with open(result["output_path"]) as f:
            lines = f.readlines()
        self.assertGreater(len(lines), 0)

    def test_run_extraction_auto_source_type(self):
        """run_extraction auto-detects source type from extension."""
        csv_path = str(FIXTURES / "sample_whisky.csv")
        result = run_extraction(
            artifact_path=csv_path,
            artifact_id="auto-test",
            output_dir=os.path.join(self.tmpdir, "out"),
        )
        self.assertGreater(result["successful_fields"], 0)

    def test_run_extraction_output_is_valid_jsonl(self):
        """run_extraction output is valid JSONL."""
        csv_path = str(FIXTURES / "sample_whisky.csv")
        result = run_extraction(
            artifact_path=csv_path,
            artifact_id="jsonl-test",
            output_dir=os.path.join(self.tmpdir, "out"),
        )
        with open(result["output_path"]) as f:
            for line in f:
                rec = json.loads(line)
                self.assertIn("artifact_id", rec)
                self.assertIn("field_name", rec)
                self.assertIn("verbatim_quote", rec)


# ═══════════════════════════════════════════════════════════════════════
# K. Production DB immutability
# ═══════════════════════════════════════════════════════════════════════

class TestProductionImmutability(unittest.TestCase):
    """K. Production DB unchanged by all extraction tests."""

    def test_production_db_sha(self):
        """Production DB SHA matches known value."""
        sha = _sha256(PRODUCTION_DB)
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
# L. End-to-end: P500-H artifact → P500-I extraction
# ═══════════════════════════════════════════════════════════════════════

class TestEndToEnd(unittest.TestCase):
    """L. P500-H artifact → extractor → extraction output."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="p500i_e2e_")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_csv_artifact_flow(self):
        """P500-H CSV → extract → JSONL output with correct provenance."""
        csv_path = str(FIXTURES / "sample_whisky.csv")
        result = run_extraction(
            artifact_path=csv_path,
            artifact_id="e2e-csv",
            output_dir=os.path.join(self.tmpdir, "out"),
        )
        self.assertEqual(result["artifact_id"], "e2e-csv")
        self.assertFalse(result["is_blocked"])
        # Read back output
        with open(result["output_path"]) as f:
            records = [json.loads(line) for line in f]
        self.assertGreater(len(records), 0)
        for rec in records:
            self.assertEqual(rec["artifact_id"], "e2e-csv")
            self.assertEqual(rec["content_hash"], _sha256(csv_path))

    def test_html_artifact_flow(self):
        """P500-H HTML → extract → JSONL output."""
        html_path = str(FIXTURES / "sample_web_artifact.html")
        result = run_extraction(
            artifact_path=html_path,
            artifact_id="e2e-html",
            output_dir=os.path.join(self.tmpdir, "out2"),
        )
        self.assertEqual(result["artifact_id"], "e2e-html")
        self.assertFalse(result["is_blocked"])
        with open(result["output_path"]) as f:
            records = [json.loads(line) for line in f]
        self.assertGreater(len(records), 0)
        # Verify verbatim quote from HTML
        titles = [r for r in records if r["field_name"] == "html:title"]
        self.assertGreaterEqual(len(titles), 1)
        self.assertIn("Ardbeg", titles[0]["verbatim_quote"])


if __name__ == "__main__":
    unittest.main()
