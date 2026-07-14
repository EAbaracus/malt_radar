"""
P95.4 — Real Telemetry Collector

Replaces the simulated Metrics class with a collector that aggregates
real measured values from HttpFetcher, ContentCache, adapters, and
pipeline stages.

Every metric is measured, never estimated or hardcoded.
"""
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class Telemetry:
    """Collects and reports measured metrics across all pipeline stages.

    Each subsystem pushes its telemetry snapshot; Telemetry aggregates
    and writes structured reports. No values are estimated — every
    counter is populated by actual execution.
    """

    def __init__(self):
        self._metrics: Dict[str, Any] = {
            # HTTP acquisition
            "pages_downloaded": 0,
            "pages_failed": 0,
            "requests_total": 0,
            "retries_total": 0,
            "bytes_downloaded": 0,
            "fixture_hits": 0,
            # Cache
            "cache_hits": 0,
            "cache_misses": 0,
            "cache_writes": 0,
            "pages_skipped_by_cache": 0,
            "pages_changed": 0,
            # Pipeline stages
            "adapter_executions": 0,
            "adapter_failures": 0,
            "extraction_executions": 0,
            "qualification_executions": 0,
            "certification_executions": 0,
            "evidence_records_generated": 0,
            # Discovery
            "whiskies_discovered_new": 0,
            "whiskies_enriched_existing": 0,
            "new_evidence_records_collected": 0,
            "sources_contributing": set(),
            # Timestamps
            "pipeline_started_at": None,
            "pipeline_finished_at": None,
        }
        # Detailed logs for jsonl export
        self._http_log: List[Dict] = []

    def ingest_http_telemetry(self, fetcher_telemetry: Dict):
        """Ingest measured telemetry from HttpFetcher."""
        for key in ("pages_downloaded", "pages_failed", "requests_total",
                    "retries_total", "bytes_downloaded", "fixture_hits"):
            if key in fetcher_telemetry:
                self._metrics[key] = fetcher_telemetry[key]

    def ingest_cache_telemetry(self, cache_telemetry: Dict):
        """Ingest measured telemetry from ContentCache."""
        keys = {
            "cache_hits": "cache_hits",
            "cache_misses": "cache_misses",
            "cache_writes": "cache_writes",
            "pages_skipped_by_cache": "pages_skipped_unchanged",
            "pages_changed": "pages_changed",
        }
        for metric_key, telemetry_key in keys.items():
            if telemetry_key in cache_telemetry:
                self._metrics[metric_key] = cache_telemetry[telemetry_key]

    def log_http_request(self, entry: Dict):
        """Log a single HTTP request to the execution log."""
        self._http_log.append(entry)

    def record_adapter_result(self, success: bool):
        if success:
            self._metrics["adapter_executions"] += 1
        else:
            self._metrics["adapter_failures"] += 1

    def record_extraction(self):
        self._metrics["extraction_executions"] += 1

    def record_qualification(self):
        self._metrics["qualification_executions"] += 1

    def record_certification(self):
        self._metrics["certification_executions"] += 1

    def record_evidence(self, count: int):
        self._metrics["evidence_records_generated"] += count

    def record_new_whisky(self, count: int = 1):
        self._metrics["whiskies_discovered_new"] += count

    def record_enriched_whisky(self, count: int = 1):
        self._metrics["whiskies_enriched_existing"] += count

    def record_evidence_collected(self, count: int):
        self._metrics["new_evidence_records_collected"] += count

    def record_source(self, source: str):
        self._metrics["sources_contributing"].add(source)

    def start_timer(self):
        self._metrics["pipeline_started_at"] = datetime.now(timezone.utc).isoformat()

    def stop_timer(self):
        self._metrics["pipeline_finished_at"] = datetime.now(timezone.utc).isoformat()

    # ------------------------------------------------------------------
    # Reports
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a JSON-serializable dict."""
        d = dict(self._metrics)
        d["sources_contributing"] = sorted(d["sources_contributing"])
        return d

    def write_http_log(self, path: str):
        """Write the HTTP execution log as JSONL."""
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            for entry in self._http_log:
                f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
        logger.info(f"HTTP execution log written: {path} ({len(self._http_log)} entries)")

    def write_telemetry_report(self, path: str):
        """Write the telemetry report markdown."""
        m = self._metrics
        lines = [
            "# P95 Telemetry Report",
            "",
            "All metrics are **measured** (none estimated, none hardcoded).",
            "",
            "## Acquisition Metrics",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Pages Downloaded | {m['pages_downloaded']} |",
            f"| Pages Failed | {m['pages_failed']} |",
            f"| Total HTTP Requests | {m['requests_total']} |",
            f"| Total Retries | {m['retries_total']} |",
            f"| Bytes Downloaded | {m['bytes_downloaded']} |",
            f"| Fixture Hits | {m['fixture_hits']} |",
            "",
            "## Cache Metrics",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Cache Hits | {m['cache_hits']} |",
            f"| Cache Misses | {m['cache_misses']} |",
            f"| Cache Writes | {m['cache_writes']} |",
            f"| Pages Skipped (Unchanged) | {m['pages_skipped_by_cache']} |",
            f"| Pages Changed | {m['pages_changed']} |",
            "",
            "## Pipeline Metrics",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Adapter Executions | {m['adapter_executions']} |",
            f"| Adapter Failures | {m['adapter_failures']} |",
            f"| Extraction Executions | {m['extraction_executions']} |",
            f"| Qualification Executions | {m['qualification_executions']} |",
            f"| Certification Executions | {m['certification_executions']} |",
            f"| Evidence Records Generated | {m['evidence_records_generated']} |",
            "",
            "## Discovery Metrics",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| New Whiskies Discovered | {m['whiskies_discovered_new']} |",
            f"| Existing Whiskies Enriched | {m['whiskies_enriched_existing']} |",
            f"| New Evidence Records Collected | {m['new_evidence_records_collected']} |",
            f"| Sources Contributing | {', '.join(m['sources_contributing']) or 'none'} |",
            "",
            "## Timing",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Pipeline Started | {m['pipeline_started_at'] or 'N/A'} |",
            f"| Pipeline Finished | {m['pipeline_finished_at'] or 'N/A'} |",
            "",
            "---",
            "*All values originate from actual execution counters. "
            "No estimated or fabricated metrics.*",
        ]
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        logger.info(f"Telemetry report written: {path}")