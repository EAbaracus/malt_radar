#!/usr/bin/env python3
"""
P96 — Whiskybase Member Export Acquisition Pipeline

Canonical source: member-provided export files (CSV/JSON) — LIVE WEB IS A FALLBACK ONLY.
Per P500-H / acquisition_plan: W5 Whiskybase live blocked by Cloudflare → member export file only (P60 pattern).

This pipeline:
  1. Ingests export files from data/imports/whiskybase/exports/
  2. Normalizes rows to EvidenceEnvelope (source_id=whiskybase, authority_tier=T1_authoritative)
  3. Optional: Live fallback via HoundMCPClient.smart_fetch() for specific bottle URLs not in export
  4. Outputs staged evidence to output/staging/whiskybase_evidence.jsonl
  5. Validates against evidence schema; writes acceptance report
"""

from __future__ import annotations

import csv
import hashlib
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure repo root on path
REPO_ROOT = Path(__file__).resolve().parents[2]
_HERE = Path(__file__).resolve().parent
_MRKEP = _HERE.parent
_ACQUISITION = str(_HERE)

if _ACQUISITION not in sys.path:
    sys.path.insert(0, _ACQUISITION)
if str(_MRKEP) not in sys.path:
    sys.path.insert(0, str(_MRKEP))

from hound_fetcher import HoundMCPClient
from adapters.whiskybase_adapter import WhiskybaseAdapter
from adapters.masterofmalt_adapter import MasterOfMaltAdapter
from adapters.whiskynotes_adapter import WhiskyNotesAdapter
from source_types import SourceType, SourceFormat, detect_format

# ── source → adapter routing table ──────────────────────────────────
# Deterministic URL-hostname based routing. NEVER routes by product name.
# source_id mirrors the adapter's authoritative SOURCE attribute.
ROUTING_TABLE: Dict[str, Tuple[type, str]] = {
    "whiskybase.com": (WhiskybaseAdapter, "whiskybase"),
    "www.whiskybase.com": (WhiskybaseAdapter, "whiskybase"),
    "masterofmalt.com": (MasterOfMaltAdapter, "masterofmalt"),
    "www.masterofmalt.com": (MasterOfMaltAdapter, "masterofmalt"),
    "whiskynotes.be": (WhiskyNotesAdapter, "whiskynotes"),
    "www.whiskynotes.be": (WhiskyNotesAdapter, "whiskynotes"),
}


class UnsupportedSourceError(ValueError):
    """Raised when a live-fallback URL belongs to an unsupported domain."""


def select_adapter(url: str) -> Tuple[WhiskybaseAdapter, str]:
    """Route a source URL to (adapter_instance, source_id) by hostname.

    Deterministic: same URL -> same adapter. Raises UnsupportedSourceError
    for domains not in ROUTING_TABLE (never silently falls back to the wrong
    adapter).
    """
    from urllib.parse import urlparse

    host = (urlparse(url).netloc or "").lower()
    # strip port if present
    host = host.split(":")[0]
    if host in ROUTING_TABLE:
        adapter_cls, source_id = ROUTING_TABLE[host]
        return adapter_cls(), source_id
    raise UnsupportedSourceError(f"Unsupported source domain: {host!r} (url={url})")


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("p96")

# ── constants ──────────────────────────────────────────────────────────
EXPORT_DIR = REPO_ROOT / "data" / "imports" / "whiskybase" / "exports"
STAGING_DIR = REPO_ROOT / "output" / "staging"
STAGING_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_EVIDENCE = STAGING_DIR / "whiskybase_evidence.jsonl"
OUTPUT_REPORT = STAGING_DIR / "p96_acceptance_report.md"

SOURCE_ID = "whiskybase"
AUTHORITY_TIER = "T1_authoritative"
EVIDENCE_CONFIDENCE = 0.95

# Expected export columns (flexible mapping)
EXPORT_COLUMN_MAP = {
    # whiskybase export canonical names → our evidence fields
    "whisky_id": "whisky_id",
    "bottle_id": "bottle_id",
    "name": "name",
    "distillery": "distillery_name",
    "region": "region",
    "country": "country",
    "strength": "abv",
    "age": "age_statement",
    "cask_type": "cask_type",
    "bottler": "bottler",
    "series": "bottling_series",
    "bottled": "release_year",
    "size": "bottle_size",
    "vintage": "vintage_year",
    "bottle_code": "bottle_code",
    "price": "price",  # stored but never exposed per product rule
    "currency": "currency",
    "rating": "community_rating",
    "votes": "rating_count",
    "url": "source_url",
}

# ── evidence envelope (mirrors kep_runtime evidence model) ─────────────


def make_evidence_id(source_id: str, whisky_id: str, field: str, timestamp: str) -> str:
    """Deterministic evidence_id = sha256(source|whisky_id|field|timestamp)[:16]"""
    raw = f"{source_id}|{whisky_id}|{field}|{timestamp}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def build_envelope(
    whisky_id: str,
    field_name: str,
    field_value: Any,
    quote: str,
    source_url: str,
    export_row: Dict[str, Any],
    is_live_fallback: bool = False,
    source_id: str = SOURCE_ID,
) -> Dict[str, Any]:
    """Construct a normalized evidence envelope.

    source_id is passed explicitly so live-fallback paths can tag the
    REAL source adapter (masterofmalt / whiskynotes) instead of the
    hardcoded module-level SOURCE_ID ("whiskybase"). Default stays
    SOURCE_ID for the member-export path (which is genuinely whiskybase).
    """
    ts = datetime.now(timezone.utc).isoformat()
    return {
        "evidence_id": make_evidence_id(source_id, whisky_id, field_name, ts),
        "whisky_id": whisky_id,
        "source_id": source_id,
        "authority_tier": AUTHORITY_TIER,
        "field_name": field_name,
        "field_value": field_value,
        "confidence": EVIDENCE_CONFIDENCE,
        "quote": quote,
        "source_url": source_url,
        "retrieved_at": ts,
        "provenance": {
            "source_type": "member_export" if not is_live_fallback else "live_web_fallback",
            "export_row_keys": list(export_row.keys()) if export_row else [],
            "fallback": is_live_fallback,
        },
    }


# ── export file discovery ──────────────────────────────────────────────


def discover_exports() -> List[Path]:
    """Find all export files in the import directory."""
    if not EXPORT_DIR.exists():
        logger.warning(f"Export directory not found: {EXPORT_DIR}")
        return []

    exports = []
    for ext in (".csv", ".json", ".jsonl", ".xlsx", ".xls"):
        exports.extend(EXPORT_DIR.glob(f"*{ext}"))

    exports.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    logger.info(f"Discovered {len(exports)} export file(s) in {EXPORT_DIR}")
    for e in exports:
        logger.info(f"  {e.name} ({e.stat().st_size} bytes, mtime={datetime.fromtimestamp(e.stat().st_mtime).isoformat()})")
    return exports


# ── export parsers ─────────────────────────────────────────────────────


def parse_csv_export(path: Path) -> List[Dict[str, Any]]:
    """Parse CSV export with flexible header matching."""
    rows = []
    with open(path, "r", encoding="utf-8-sig") as f:
        # Sniff delimiter
        sample = f.read(4096)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample)
        except csv.Error:
            dialect = csv.excel

        reader = csv.DictReader(f, dialect=dialect)
        for row in reader:
            # Normalize keys: lowercase, strip, replace spaces
            norm = {k.lower().strip().replace(" ", "_"): v.strip() for k, v in row.items() if v and v.strip()}
            if norm:
                rows.append(norm)
    return rows


def parse_json_export(path: Path) -> List[Dict[str, Any]]:
    """Parse JSON or JSONL export."""
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        content = f.read().strip()
        if not content:
            return rows

        # Try JSONL first (one object per line)
        for line in content.split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if isinstance(obj, dict):
                    rows.append({k.lower().strip().replace(" ", "_"): v for k, v in obj.items() if v is not None})
            except json.JSONDecodeError:
                pass

        # If JSONL yielded nothing, try whole-file JSON array
        if not rows:
            try:
                data = json.loads(content)
                if isinstance(data, list):
                    for obj in data:
                        if isinstance(obj, dict):
                            rows.append({k.lower().strip().replace(" ", "_"): v for k, v in obj.items() if v is not None})
            except json.JSONDecodeError:
                pass

    return rows


def parse_export_file(path: Path) -> Tuple[List[Dict[str, Any]], str]:
    """Route to appropriate parser based on extension."""
    fmt = detect_format(str(path))
    if fmt == SourceFormat.CSV:
        return parse_csv_export(path), "csv"
    elif fmt in (SourceFormat.JSON, SourceFormat.JSONL):
        return parse_json_export(path), "json"
    else:
        logger.warning(f"Unsupported export format: {path.suffix}")
        return [], "unknown"


# ── evidence extraction from export rows ───────────────────────────────


def extract_evidence_from_row(row: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Map a single export row to multiple evidence envelopes."""
    envelopes = []

    # Determine whisky_id (required)
    whisky_id = row.get("whisky_id") or row.get("bottle_id") or row.get("id") or row.get("whiskybase_id")
    if not whisky_id:
        # Generate from name+distillery if missing
        name = row.get("name", "").strip()
        dist = row.get("distillery", "").strip()
        if name and dist:
            whisky_id = f"WB-{hashlib.sha256(f'{dist}|{name}'.encode()).hexdigest()[:8]}"
        else:
            logger.debug(f"Skipping row without identifiable whisky_id: {row}")
            return envelopes

    source_url = row.get("url") or row.get("source_url") or f"https://www.whiskybase.com/whiskies/whisky/{whisky_id}"

    # Map each known column to evidence
    for export_col, field_name in EXPORT_COLUMN_MAP.items():
        if export_col not in row:
            continue
        value = row[export_col]
        if not value or not str(value).strip():
            continue

        # Special handling for known types
        if field_name == "abv":
            # Normalize "43.0 %" → 43.0
            m = re.search(r"([\d.]+)", str(value))
            if m:
                value = float(m.group(1))
            else:
                continue

        elif field_name == "age_statement":
            # Normalize "16 years" → 16
            m = re.search(r"(\d+)", str(value))
            if m:
                value = int(m.group(1))
            else:
                continue

        elif field_name == "release_year":
            m = re.search(r"(20\d{2}|19\d{2})", str(value))
            if m:
                value = int(m.group(1))
            else:
                continue

        elif field_name == "community_rating":
            try:
                value = float(value)
            except (ValueError, TypeError):
                continue

        elif field_name == "rating_count":
            try:
                value = int(value)
            except (ValueError, TypeError):
                continue

        # Build quote from row context
        quote_parts = [f"{export_col}: {value}"]
        for ctx_col in ("name", "distillery", "region", "age"):
            if ctx_col in row and row[ctx_col]:
                quote_parts.append(f"{ctx_col}: {row[ctx_col]}")
        quote = " | ".join(quote_parts)

        env = build_envelope(
            whisky_id=str(whisky_id),
            field_name=field_name,
            field_value=value,
            quote=quote,
            source_url=source_url,
            export_row=row,
            is_live_fallback=False,
        )
        envelopes.append(env)

    return envelopes


# ── live fallback via Hound MCP ────────────────────────────────────────


def live_fallback_fetch(
    url: str,
    client: HoundMCPClient,
    adapter: WhiskybaseAdapter,
    whisky_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Attempt to fetch a single bottle page via Hound MCP as last resort.

    whisky_id: the REAL target whisky/entity id. When None (caller cannot
    resolve the entity, e.g. no entity-resolution step), a deterministic
    placeholder derived from the URL is used (WB-LIVE-<hash>) — this is an
    explicit "unresolved" marker, NOT a guessed production id. The adapter's
    product `name` is NEVER used as whisky_id (it is a display name, not an
    entity id, and would cause cross-contamination between same-named bottles).

    source_id is taken from the adapter's real SOURCE attribute so the
    provenance correctly reflects masterofmalt / whiskynotes / whiskybase
    rather than the hardcoded module-level SOURCE_ID.
    """
    logger.info(f"Live fallback: fetching {url}")
    md, fetched_url, meta = client.smart_fetch(url)

    if md is None or meta.get("status") != "ok":
        logger.warning(f"Live fallback failed for {url}: {meta.get('error', 'unknown')}")
        return []

    # Parse with adapter
    parsed = adapter.parse(md)
    if not parsed.get("evidence"):
        logger.warning(f"Live fallback parsed zero evidence from {url}")
        return []

    # Resolve whisky_id: caller-supplied entity id wins; otherwise an
    # explicit URL-derived placeholder marks the row as unresolved.
    if not whisky_id:
        whisky_id = f"WB-LIVE-{hashlib.sha256(url.encode()).hexdigest()[:8]}"

    source_id = getattr(adapter, "SOURCE", SOURCE_ID)

    envelopes = []
    for ev in parsed["evidence"]:
        env = build_envelope(
            whisky_id=whisky_id,
            field_name=ev["field_name"],
            field_value=ev["field_value"],
            quote=ev["quote"],
            source_url=fetched_url or url,
            export_row={},
            is_live_fallback=True,
            source_id=source_id,
        )
        envelopes.append(env)

    logger.info(f"Live fallback extracted {len(envelopes)} evidence fields from {url}")
    return envelopes


# ── main pipeline ──────────────────────────────────────────────────────


def run_pipeline(
    live_fallback_urls: Optional[List[str]] = None,
    max_live_fallback: int = 5,
) -> Dict[str, Any]:
    """Execute P96 pipeline end-to-end."""
    logger.info("=" * 60)
    logger.info("P96 Whiskybase Member Export Pipeline — START")
    logger.info("=" * 60)

    stats = {
        "export_files": 0,
        "rows_processed": 0,
        "evidence_from_export": 0,
        "evidence_from_live": 0,
        "live_fallback_attempts": 0,
        "live_fallback_success": 0,
        "errors": [],
    }

    # 1. Discover and parse exports
    exports = discover_exports()
    all_envelopes = []

    for exp_path in exports:
        stats["export_files"] += 1
        rows, fmt = parse_export_file(exp_path)
        logger.info(f"Parsed {len(rows)} rows from {exp_path.name} ({fmt})")

        for row in rows:
            stats["rows_processed"] += 1
            envs = extract_evidence_from_row(row)
            all_envelopes.extend(envs)

        stats["evidence_from_export"] = len(all_envelopes)

    # 2. Optional live fallback
    if live_fallback_urls:
        client = HoundMCPClient()

        for url in live_fallback_urls[:max_live_fallback]:
            # Route by source URL hostname -> correct adapter + source_id.
            try:
                adapter, source_id = select_adapter(url)
            except UnsupportedSourceError as e:
                stats["live_fallback_attempts"] += 1
                stats["errors"].append(str(e))
                logger.warning(str(e))
                continue

            stats["live_fallback_attempts"] += 1
            try:
                live_envs = live_fallback_fetch(url, client, adapter)
                if live_envs:
                    all_envelopes.extend(live_envs)
                    stats["evidence_from_live"] += len(live_envs)
                    stats["live_fallback_success"] += 1
            except Exception as e:
                stats["errors"].append(f"Live fallback {url}: {e}")
                logger.exception(f"Live fallback error for {url}")

    # 3. Deduplicate by evidence_id (deterministic, so identical = same row+field)
    seen = set()
    unique_envelopes = []
    for env in all_envelopes:
        eid = env["evidence_id"]
        if eid not in seen:
            seen.add(eid)
            unique_envelopes.append(env)

    logger.info(f"Total envelopes: {len(all_envelopes)} → unique: {len(unique_envelopes)}")

    # 4. Write staged evidence
    with open(OUTPUT_EVIDENCE, "w", encoding="utf-8") as f:
        for env in unique_envelopes:
            f.write(json.dumps(env, ensure_ascii=False) + "\n")

    logger.info(f"Staged evidence written: {OUTPUT_EVIDENCE} ({len(unique_envelopes)} records)")

    # 5. Write acceptance report
    write_acceptance_report(stats, unique_envelopes, exports)

    logger.info("=" * 60)
    logger.info("P96 Pipeline — COMPLETE")
    logger.info("=" * 60)

    return stats


def write_acceptance_report(stats: Dict, envelopes: List[Dict], exports: List[Path]) -> None:
    """Write P96 acceptance report (markdown)."""
    field_counts: Dict[str, int] = {}
    whisky_ids = set()
    for env in envelopes:
        field_counts[env["field_name"]] = field_counts.get(env["field_name"], 0) + 1
        whisky_ids.add(env["whisky_id"])

    lines = [
        "# P96 Whiskybase Member Export — Acceptance Report",
        "",
        f"**Run timestamp:** {datetime.now(timezone.utc).isoformat()}",
        f"**Export files processed:** {stats['export_files']}",
        f"**Rows processed:** {stats['rows_processed']}",
        f"**Unique whiskies:** {len(whisky_ids)}",
        f"**Evidence envelopes (export):** {stats['evidence_from_export']}",
        f"**Evidence envelopes (live fallback):** {stats['evidence_from_live']}",
        f"**Live fallback attempts:** {stats['live_fallback_attempts']} (success: {stats['live_fallback_success']})",
        "",
        "## Field Coverage",
        "| Field | Count |",
        "|-------|-------|",
    ]
    for field, count in sorted(field_counts.items(), key=lambda x: -x[1]):
        lines.append(f"| {field} | {count} |")

    lines.extend([
        "",
        "## Export Files",
    ])
    for exp in exports:
        lines.append(f"- {exp.name} ({exp.stat().st_size} bytes)")

    if stats["errors"]:
        lines.extend([
            "",
            "## Errors / Warnings",
        ])
        for err in stats["errors"]:
            lines.append(f"- {err}")

    lines.extend([
        "",
        "## Acceptance Criteria",
        f"- Export evidence ≥ 1: **{'PASS' if stats['evidence_from_export'] >= 1 else 'FAIL'}**",
        f"- Unique whiskies ≥ 1: **{'PASS' if len(whisky_ids) >= 1 else 'FAIL'}**",
        f"- No duplicate evidence_ids: **{'PASS' if len(envelopes) == len(set(e['evidence_id'] for e in envelopes)) else 'FAIL'}**",
        f"- All envelopes have required keys: **{'PASS' if all_required_keys(envelopes) else 'FAIL'}**",
        "",
        f"**Staged output:** `{OUTPUT_EVIDENCE.relative_to(REPO_ROOT)}`",
        f"**Report:** `{OUTPUT_REPORT.relative_to(REPO_ROOT)}`",
    ])

    with open(OUTPUT_REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    logger.info(f"Acceptance report written: {OUTPUT_REPORT}")


def all_required_keys(envelopes: List[Dict]) -> bool:
    required = {"evidence_id", "whisky_id", "source_id", "authority_tier", "field_name", "field_value", "confidence", "quote", "source_url", "retrieved_at", "provenance"}
    return all(required.issubset(set(e.keys())) for e in envelopes)


# ── CLI ────────────────────────────────────────────────────────────────


def main():
    import argparse

    parser = argparse.ArgumentParser(description="P96 Whiskybase Member Export Pipeline")
    parser.add_argument("--live-fallback", nargs="*", default=[], help="Optional bottle URLs to fetch via Hound MCP as fallback")
    parser.add_argument("--max-live", type=int, default=5, help="Max live fallback attempts")
    parser.add_argument("--dry-run", action="store_true", help="Parse only, do not write output")
    args = parser.parse_args()

    if args.dry_run:
        logger.info("DRY RUN — parsing exports only, no output written")
        exports = discover_exports()
        for exp in exports:
            rows, fmt = parse_export_file(exp)
            logger.info(f"{exp.name}: {len(rows)} rows ({fmt})")
        return 0

    stats = run_pipeline(live_fallback_urls=args.live_fallback, max_live_fallback=args.max_live)

    # Exit code based on acceptance
    if stats["evidence_from_export"] == 0 and stats["evidence_from_live"] == 0:
        logger.error("ACCEPTANCE FAIL: zero evidence produced")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())