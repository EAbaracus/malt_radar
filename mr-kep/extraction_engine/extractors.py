"""Extractor adapters — one per supported source format (P500-I §2).

Each adapter implements the Extractor protocol:
    def extract(artifact_path: str, source_meta: SourceMeta) -> list[ExtractionRecord]

Real parsers: csv (stdlib), json (stdlib), HTML (bs4), PDF (pdfminer), EPUB (ebooklib).
"""

from __future__ import annotations

import csv
import hashlib
import html.parser
import io
import json
import os
import re
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

# Canonical import path setup
_ENG_ROOT = Path(__file__).resolve().parent
if str(_ENG_ROOT) not in sys.path:
    sys.path.insert(0, str(_ENG_ROOT))
from extraction_record import (
    ExtractionRecord, ExtractionResult, ExtractionStatus,
    ExtractionError, MissingArtifactError, CorruptArtifactError,
    UnsupportedFormatError, ZeroFieldsError,
)


# ── Shared helpers ───────────────────────────────────────────────────


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(65536), b""):
            h.update(blk)
    return h.hexdigest()


def _read_bytes(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()


def _read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def _source_location(loc_type: str, value: str) -> str:
    """Canonical source location string."""
    return f"{loc_type}:{value}"


# ── Source metadata bag ──────────────────────────────────────────────

class SourceMeta:
    """Bag of metadata for an extraction request."""
    __slots__ = ("artifact_id", "source_type", "source_identifier", "source_uri")

    def __init__(
        self, artifact_id: str, source_type: str,
        source_identifier: str, source_uri: str = "",
    ):
        self.artifact_id = artifact_id
        self.source_type = source_type
        self.source_identifier = source_identifier
        self.source_uri = source_uri


# ── Base ─────────────────────────────────────────────────────────────

class BaseExtractor(ABC):
    """Abstract extractor. Each subclass handles one format."""

    SUPPORTED_FORMATS: set[str] = set()

    @abstractmethod
    def _do_extract(self, path: str, meta: SourceMeta) -> list[ExtractionRecord]:
        ...

    def extract(self, path: str, meta: SourceMeta) -> ExtractionResult:
        if not os.path.isfile(path):
            raise MissingArtifactError(f"artifact not found: {path}")
        try:
            sha = _sha256_file(path)
            records = self._do_extract(path, meta)
        except ExtractionError:
            raise
        except Exception as e:
            raise CorruptArtifactError(
                f"failed to extract {path}: {e}"
            )

        # Attach content_hash to each record
        finalized: list[ExtractionRecord] = []
        for r in records:
            finalized.append(ExtractionRecord(
                artifact_id=r.artifact_id,
                source_type=r.source_type,
                source_identifier=r.source_identifier,
                source_uri=r.source_uri,
                field_name=r.field_name,
                extracted_value=r.extracted_value,
                verbatim_quote=r.verbatim_quote,
                source_location=r.source_location,
                content_hash=sha,
                extraction_status=r.extraction_status,
            ))

        successful = [r for r in finalized if r.extraction_status == "extracted"]
        skipped = [r for r in finalized if r.extraction_status == "skipped"]
        failed = [r for r in finalized if r.extraction_status == "failed"]

        return ExtractionResult(
            artifact_id=meta.artifact_id,
            artifact_path=path,
            records=tuple(finalized),
            total_fields=len(finalized),
            successful_fields=len(successful),
            skipped_fields=len(skipped),
            failed_fields=len(failed),
            is_blocked=(len(successful) == 0),
        )


# ── CSV extractor ────────────────────────────────────────────────────

class CsvExtractor(BaseExtractor):
    """Extract structured fields from CSV."""

    SUPPORTED_FORMATS = {"csv"}

    def _do_extract(self, path: str, meta: SourceMeta) -> list[ExtractionRecord]:
        records: list[ExtractionRecord] = []
        try:
            text = _read_text(path)
            reader = csv.DictReader(io.StringIO(text))
            if not reader.fieldnames:
                return []
            for row_num, row in enumerate(reader, start=1):
                for field in reader.fieldnames:
                    val = row.get(field, "").strip()
                    if not val:
                        continue
                    # Verbatim quote = the cell value from the raw file
                    records.append(ExtractionRecord(
                        artifact_id=meta.artifact_id,
                        source_type=meta.source_type,
                        source_identifier=meta.source_identifier,
                        source_uri=meta.source_uri,
                        field_name=f"csv:{field}",
                        extracted_value=val,
                        verbatim_quote=val,
                        source_location=_source_location("row", str(row_num)),
                        content_hash="",  # filled by base
                        extraction_status=ExtractionStatus.SUCCESS.value,
                    ))
        except (csv.Error, IOError, OSError) as e:
            raise CorruptArtifactError(f"CSV parse failed: {path}: {e}")
        return records


# ── JSON extractor ───────────────────────────────────────────────────

class JsonExtractor(BaseExtractor):
    """Extract top-level string fields from JSON."""

    SUPPORTED_FORMATS = {"json", "jsonl"}

    def _do_extract(self, path: str, meta: SourceMeta) -> list[ExtractionRecord]:
        records: list[ExtractionRecord] = []
        try:
            text = _read_text(path)
            data = json.loads(text)
        except (json.JSONDecodeError, IOError, OSError) as e:
            raise CorruptArtifactError(f"JSON parse failed: {path}: {e}")

        if isinstance(data, dict):
            self._extract_value(data, meta, records, "")
        elif isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, (dict, list)):
                    self._extract_value(item, meta, records, f"[{i}]")
                elif isinstance(item, (str, int, float)):
                    records.append(self._mk_rec(meta, f"[{i}]", str(item), str(item), f"array[{i}]"))
        return records

    def _extract_value(
        self, data, meta: SourceMeta,
        records: list, prefix: str,
    ):
        if isinstance(data, dict):
            for key, val in data.items():
                field_name = f"{prefix}.{key}" if prefix else key
                if isinstance(val, dict):
                    self._extract_value(val, meta, records, field_name)
                elif isinstance(val, list):
                    for j, item in enumerate(val):
                        if isinstance(item, (dict, list)):
                            self._extract_value(item, meta, records, f"{field_name}[{j}]")
                        elif isinstance(item, (str, int, float)):
                            records.append(self._mk_rec(meta, f"{field_name}[{j}]", str(item), str(item), f"json:list[{j}]"))
                elif isinstance(val, str) and val.strip():
                    records.append(self._mk_rec(meta, field_name, val.strip(), val.strip(), f"json-key:{key}"))
                elif isinstance(val, (int, float)):
                    records.append(self._mk_rec(meta, field_name, str(val), str(val), f"json-key:{key}"))
        elif isinstance(data, list):
            for j, item in enumerate(data):
                if isinstance(item, (dict, list)):
                    self._extract_value(item, meta, records, f"{prefix}[{j}]")
                elif isinstance(item, (str, int, float)):
                    records.append(self._mk_rec(meta, f"{prefix}[{j}]", str(item), str(item), f"json:list[{j}]"))

    def _mk_rec(self, meta: SourceMeta, field_name: str, value: str, quote: str, location: str) -> ExtractionRecord:
        return ExtractionRecord(
            artifact_id=meta.artifact_id,
            source_type=meta.source_type,
            source_identifier=meta.source_identifier,
            source_uri=meta.source_uri,
            field_name=field_name,
            extracted_value=value,
            verbatim_quote=quote,
            source_location=_source_location("json", location),
            content_hash="",
            extraction_status=ExtractionStatus.SUCCESS.value,
        )


# ── HTML / web capture extractor ─────────────────────────────────────

class HtmlExtractor(BaseExtractor):
    """Extract text content from captured web artifacts (HTML)."""

    SUPPORTED_FORMATS = {"html", "htm"}

    def _do_extract(self, path: str, meta: SourceMeta) -> list[ExtractionRecord]:
        records: list[ExtractionRecord] = []
        try:
            from bs4 import BeautifulSoup
            text = _read_text(path)
            soup = BeautifulSoup(text, "html.parser")
        except ImportError:
            # Fallback: HTMLParser from stdlib (limited)
            return self._fallback_html_parse(path, meta)
        except Exception as e:
            raise CorruptArtifactError(f"HTML parse failed: {path}: {e}")

        # Title
        title_tag = soup.find("title")
        if title_tag and title_tag.get_text(strip=True):
            t = title_tag.get_text(strip=True)
            records.append(ExtractionRecord(
                artifact_id=meta.artifact_id,
                source_type=meta.source_type,
                source_identifier=meta.source_identifier,
                source_uri=meta.source_uri,
                field_name="html:title",
                extracted_value=t,
                verbatim_quote=t,
                source_location=_source_location("tag", "title"),
                content_hash="",
                extraction_status=ExtractionStatus.SUCCESS.value,
            ))

        # Meta description
        meta_tag = soup.find("meta", attrs={"name": "description"})
        if meta_tag:
            mc = meta_tag.get("content")
            if mc and isinstance(mc, str) and mc.strip():
                c = mc.strip()
                records.append(ExtractionRecord(
                    artifact_id=meta.artifact_id,
                    source_type=meta.source_type,
                    source_identifier=meta.source_identifier,
                    source_uri=meta.source_uri,
                    field_name="html:meta_description",
                    extracted_value=c,
                    verbatim_quote=c,
                    source_location=_source_location("meta", "description"),
                    content_hash="",
                    extraction_status=ExtractionStatus.SUCCESS.value,
                ))

        # H1 headings
        for i, h1 in enumerate(soup.find_all("h1")):
            txt = h1.get_text(strip=True)
            if txt:
                records.append(ExtractionRecord(
                    artifact_id=meta.artifact_id,
                    source_type=meta.source_type,
                    source_identifier=meta.source_identifier,
                    source_uri=meta.source_uri,
                    field_name=f"html:h1[{i}]",
                    extracted_value=txt,
                    verbatim_quote=txt,
                    source_location=_source_location("h1", str(i)),
                    content_hash="",
                    extraction_status=ExtractionStatus.SUCCESS.value,
                ))

        # All paragraph text
        for i, p in enumerate(soup.find_all("p")):
            txt = p.get_text(strip=True)
            if txt and len(txt) > 20:  # skip short fragments
                records.append(ExtractionRecord(
                    artifact_id=meta.artifact_id,
                    source_type=meta.source_type,
                    source_identifier=meta.source_identifier,
                    source_uri=meta.source_uri,
                    field_name=f"html:p[{i}]",
                    extracted_value=txt[:500],
                    verbatim_quote=txt[:500],
                    source_location=_source_location("p", str(i)),
                    content_hash="",
                    extraction_status=ExtractionStatus.SUCCESS.value,
                ))

        return records

    def _fallback_html_parse(self, path: str, meta: SourceMeta) -> list[ExtractionRecord]:
        """Stdlib HTMLParser fallback (limited — extracts title only)."""
        from html.parser import HTMLParser
        records: list[ExtractionRecord] = []
        text = _read_text(path)

        class _TitleFinder(HTMLParser):
            def __init__(self):
                super().__init__()
                self.in_title = False
                self.title = ""

            def handle_starttag(self, tag, attrs):
                if tag == "title":
                    self.in_title = True

            def handle_endtag(self, tag):
                if tag == "title":
                    self.in_title = False

            def handle_data(self, data):
                if self.in_title:
                    self.title += data

        finder = _TitleFinder()
        finder.feed(text)
        title = finder.title.strip()
        if title:
            records.append(ExtractionRecord(
                artifact_id=meta.artifact_id,
                source_type=meta.source_type,
                source_identifier=meta.source_identifier,
                source_uri=meta.source_uri,
                field_name="html:title",
                extracted_value=title,
                verbatim_quote=title,
                source_location=_source_location("tag", "title"),
                content_hash="",
                extraction_status=ExtractionStatus.SUCCESS.value,
            ))
        return records


# ── PDF extractor ────────────────────────────────────────────────────

class PdfExtractor(BaseExtractor):
    """Extract text content from PDF using pdfminer.six."""

    SUPPORTED_FORMATS = {"pdf"}

    def _do_extract(self, path: str, meta: SourceMeta) -> list[ExtractionRecord]:
        records: list[ExtractionRecord] = []
        try:
            from pdfminer.high_level import extract_pages
            from pdfminer.layout import LTTextBox, LTTextLine, LTChar
        except ImportError as e:
            raise UnsupportedFormatError(
                f"PDF extraction requires pdfminer.six: {e}"
            )

        try:
            for page_num, page_layout in enumerate(extract_pages(path), start=1):
                page_text_parts: list[str] = []
                for element in page_layout:
                    if isinstance(element, (LTTextBox, LTTextLine)):
                        txt = element.get_text().strip()
                        if txt:
                            page_text_parts.append(txt)

                full_text = "\n".join(page_text_parts)
                if not full_text.strip():
                    continue

                # Extract as one page record
                first_line = full_text.split("\n")[0].strip()[:200]
                records.append(ExtractionRecord(
                    artifact_id=meta.artifact_id,
                    source_type=meta.source_type,
                    source_identifier=meta.source_identifier,
                    source_uri=meta.source_uri,
                    field_name=f"pdf:page[{page_num}]",
                    extracted_value=first_line if first_line else full_text[:200],
                    verbatim_quote=full_text[:500].strip(),
                    source_location=_source_location("page", str(page_num)),
                    content_hash="",
                    extraction_status=ExtractionStatus.SUCCESS.value,
                ))
        except Exception as e:
            raise CorruptArtifactError(f"PDF extraction failed: {path}: {e}")

        return records


# ── EPUB extractor ───────────────────────────────────────────────────

class EpubExtractor(BaseExtractor):
    """Extract text content from EPUB using ebooklib."""

    SUPPORTED_FORMATS = {"epub"}

    def _do_extract(self, path: str, meta: SourceMeta) -> list[ExtractionRecord]:
        records: list[ExtractionRecord] = []
        try:
            import ebooklib
            from ebooklib import epub
            book = epub.read_epub(path)
        except ImportError as e:
            raise UnsupportedFormatError(
                f"EPUB extraction requires ebooklib: {e}"
            )
        except Exception as e:
            raise CorruptArtifactError(f"EPUB open failed: {path}: {e}")

        # Title
        title = book.get_metadata("DC", "title")
        if title:
            t = title[0][0]
            records.append(ExtractionRecord(
                artifact_id=meta.artifact_id,
                source_type=meta.source_type,
                source_identifier=meta.source_identifier,
                source_uri=meta.source_uri,
                field_name="epub:title",
                extracted_value=t,
                verbatim_quote=t,
                source_location=_source_location("metadata", "title"),
                content_hash="",
                extraction_status=ExtractionStatus.SUCCESS.value,
            ))

        # Creator
        creator = book.get_metadata("DC", "creator")
        if creator:
            c = creator[0][0] if creator[0] else ""
            records.append(ExtractionRecord(
                artifact_id=meta.artifact_id,
                source_type=meta.source_type,
                source_identifier=meta.source_identifier,
                source_uri=meta.source_uri,
                field_name="epub:creator",
                extracted_value=c,
                verbatim_quote=c,
                source_location=_source_location("metadata", "creator"),
                content_hash="",
                extraction_status=ExtractionStatus.SUCCESS.value,
            ))

        # Document items (chapters)
        from bs4 import BeautifulSoup
        for item in book.get_items():
            if item.get_type() != ebooklib.ITEM_DOCUMENT:
                continue
            try:
                soup = BeautifulSoup(item.get_content(), "html.parser")
                body_text = soup.get_text(strip=True)
                if not body_text:
                    continue
                # First meaningful line
                first_line = body_text.split("\n")[0].strip()[:200]
                item_name = item.get_name()
                records.append(ExtractionRecord(
                    artifact_id=meta.artifact_id,
                    source_type=meta.source_type,
                    source_identifier=meta.source_identifier,
                    source_uri=meta.source_uri,
                    field_name=f"epub:doc:{item_name}",
                    extracted_value=first_line,
                    verbatim_quote=body_text[:500].strip(),
                    source_location=_source_location("item", item_name),
                    content_hash="",
                    extraction_status=ExtractionStatus.SUCCESS.value,
                ))
            except Exception:
                # Per-record: skip + structured log (continue)
                records.append(ExtractionRecord(
                    artifact_id=meta.artifact_id,
                    source_type=meta.source_type,
                    source_identifier=meta.source_identifier,
                    source_uri=meta.source_uri,
                    field_name="epub:parse_error",
                    extracted_value="",
                    verbatim_quote="",
                    source_location=_source_location("item", item.get_name()),
                    content_hash="",
                    extraction_status=ExtractionStatus.SKIPPED.value,
                ))

        return records


# ── Extractor router ─────────────────────────────────────────────────

FORMAT_EXTRACTOR_MAP: dict[str, BaseExtractor] = {}


def _ensure_extractors():
    if not FORMAT_EXTRACTOR_MAP:
        csv_ext = CsvExtractor()
        json_ext = JsonExtractor()
        html_ext = HtmlExtractor()
        pdf_ext = PdfExtractor()
        epub_ext = EpubExtractor()
        for ext in (csv_ext, json_ext, html_ext, pdf_ext, epub_ext):
            for fmt in ext.SUPPORTED_FORMATS:
                FORMAT_EXTRACTOR_MAP[fmt] = ext


def get_extractor(source_format: str) -> Optional[BaseExtractor]:
    """Get the extractor for a given format string (e.g. 'csv', 'pdf')."""
    _ensure_extractors()
    return FORMAT_EXTRACTOR_MAP.get(source_format.lower())


def extract_artifact(
    artifact_path: str,
    meta: SourceMeta,
    format_label: str = "",
) -> ExtractionResult:
    """Extract fields from a single raw artifact.

    Args:
        artifact_path: Path to the raw P500-H artifact file.
        meta: Source metadata (artifact_id, source_type, etc.).
        format_label: Override format detection (e.g. 'pdf').
            Auto-detected from extension if empty.

    Returns:
        ExtractionResult with all extracted records.

    Raises:
        MissingArtifactError, UnsupportedFormatError, CorruptArtifactError,
        ZeroFieldsError.
    """
    _ensure_extractors()

    if not os.path.isfile(artifact_path):
        raise MissingArtifactError(f"artifact not found: {artifact_path}")

    # Detect format
    if not format_label:
        ext = os.path.splitext(artifact_path)[1].lower().lstrip(".")
        format_label = ext

    extractor = get_extractor(format_label)
    if extractor is None:
        raise UnsupportedFormatError(
            f"no extractor for format: {format_label!r} "
            f"(artifact: {artifact_path})"
        )

    result = extractor.extract(artifact_path, meta)

    if result.is_blocked:
        msg = (
            f"zero successful extracted fields for {artifact_path}"
        )
        if result.total_fields > 0:
            msg += (
                f" (total={result.total_fields}, "
                f"skipped={result.skipped_fields}, "
                f"failed={result.failed_fields})"
            )
        raise ZeroFieldsError(msg)

    return result


__all__ = [
    "extract_artifact", "get_extractor",
    "BaseExtractor", "CsvExtractor", "JsonExtractor",
    "HtmlExtractor", "PdfExtractor", "EpubExtractor",
    "SourceMeta",
]
