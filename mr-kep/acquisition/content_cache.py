"""
P95.2 — Content-Addressed Cache

Replaces simulated in-memory change detection with a real persistent,
SHA-256 content-addressed cache. Tracks:
- SHA-256 content hash per URL
- Timestamp of first fetch and last change
- Source identifier
- Content metadata

If page hash is unchanged: skip extraction entirely.
All telemetry is measured, not estimated.
"""
import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ContentCache:
    """Persistent, content-addressed cache for acquired pages.

    Cache entries are stored as JSON lines (jsonl) for append-only durability.
    Each entry maps a URL to its SHA-256 hash + metadata.

    On lookup:
      - If URL known AND hash matches → CACHE_HIT (skip extraction)
      - If URL known AND hash differs → CHANGED (re-extract)
      - If URL unknown → NEW (first acquisition)
    """

    def __init__(self, cache_path: str):
        self.cache_path = cache_path
        self._entries: Dict[str, Dict] = {}  # url → entry
        self._dirty = False

        # Ensure directory exists
        os.makedirs(os.path.dirname(cache_path) or ".", exist_ok=True)

        self._load()

        # Telemetry (measured, never estimated)
        self.cache_hits = 0
        self.cache_misses = 0
        self.cache_writes = 0
        self.pages_changed = 0
        self.pages_skipped = 0

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self):
        """Load cache entries from disk."""
        if not os.path.exists(self.cache_path):
            logger.info(f"Cache file {self.cache_path} not found, starting fresh.")
            return

        count = 0
        try:
            with open(self.cache_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    entry = json.loads(line)
                    url = entry.get("url")
                    if url:
                        self._entries[url] = entry
                        count += 1
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Error loading cache {self.cache_path}: {e}")

        logger.info(f"Loaded {count} cache entries from {self.cache_path}")

    def _save(self):
        """Write all entries to disk atomically via temp file."""
        tmp_path = self.cache_path + ".tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                for entry in self._entries.values():
                    f.write(json.dumps(entry, sort_keys=True, ensure_ascii=False) + "\n")
            os.replace(tmp_path, self.cache_path)
            self._dirty = False
        except IOError as e:
            logger.error(f"Failed to save cache: {e}")

    def flush(self):
        """Explicit flush if auto-save is disabled."""
        if self._dirty:
            self._save()

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def lookup(self, url: str) -> Tuple[str, Optional[Dict]]:
        """Look up a URL in the cache.

        Returns (status, entry) where status is one of:
          - 'new'        — URL not in cache
          - 'unchanged'  — URL in cache, but hash not required for comparison yet
          - 'changed'    — URL in cache with prior state

        Call check_hash() after computing the actual content hash.
        """
        entry = self._entries.get(url)
        if entry is None:
            self.cache_misses += 1
            return ("new", None)
        self.cache_hits += 1
        return ("known", entry)

    def check_hash(self, url: str, content: bytes) -> Tuple[str, Dict]:
        """Full hash check: compute SHA-256, compare with cache, update state.

        Returns (status, entry):
          - 'new'        — first time seeing this URL
          - 'unchanged'  — hash matches previous → skip extraction
          - 'changed'    — hash differs from previous → re-extract
        """
        content_hash = _sha256(content)
        entry = self._entries.get(url)

        if entry is None:
            # NEW: first acquisition
            self.cache_misses += 1
            entry = {
                "url": url,
                "first_seen": _now_iso(),
                "last_changed": _now_iso(),
                "page_hashes": [content_hash],
                "current_hash": content_hash,
                "change_count": 0,
            }
            self._entries[url] = entry
            self.cache_writes += 1
            self._dirty = True
            return ("new", entry)

        # Check hash against stored current_hash
        if entry["current_hash"] == content_hash:
            # UNCHANGED: skip extraction
            self.pages_skipped += 1
            entry["last_seen_unchanged"] = _now_iso()
            if "hash not in entry['page_hashes']":
                entry["page_hashes"].append(content_hash)
            self._dirty = True
            return ("unchanged", entry)

        # CHANGED: content differs
        self.pages_changed += 1
        entry["current_hash"] = content_hash
        entry["last_changed"] = _now_iso()
        entry["change_count"] = entry.get("change_count", 0) + 1
        entry["page_hashes"].append(content_hash)
        self.cache_writes += 1
        self._dirty = True
        logger.info(f"[CACHE] Content changed for {url} (change #{entry['change_count']})")
        return ("changed", entry)

    def get_entry(self, url: str) -> Optional[Dict]:
        """Get cached entry without side effects."""
        return self._entries.get(url)

    def get_all_entries(self) -> List[Dict]:
        """Return all cached entries for reporting."""
        return list(self._entries.values())

    def get_url_count(self) -> int:
        return len(self._entries)

    def get_hash_for_url(self, url: str) -> Optional[str]:
        entry = self._entries.get(url)
        return entry["current_hash"] if entry else None

    # ------------------------------------------------------------------
    # Telemetry
    # ------------------------------------------------------------------

    def get_telemetry(self) -> Dict[str, Any]:
        """Return measured cache telemetry (never estimated)."""
        return {
            "cache_entries": self.get_url_count(),
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_writes": self.cache_writes,
            "pages_skipped_unchanged": self.pages_skipped,
            "pages_changed": self.pages_changed,
            "entries_detail": [
                {
                    "url": e["url"],
                    "current_hash": e["current_hash"][:16],
                    "change_count": e.get("change_count", 0),
                    "first_seen": e.get("first_seen"),
                    "last_changed": e.get("last_changed"),
                }
                for e in self._entries.values()
            ],
        }

    def get_incremental_stats(self) -> Dict[str, Any]:
        """Return incremental processing statistics."""
        total = self.get_url_count()
        changed = sum(1 for e in self._entries.values() if e.get("change_count", 0) > 0)
        unchanged = sum(1 for e in self._entries.values() if e.get("change_count", 0) == 0)
        return {
            "pages_discovered": total,
            "pages_changed": changed,
            "pages_unchanged": unchanged,
            "pages_skipped_by_cache": self.pages_skipped,
            "new_releases": changed,  # content change = updated release
            "updated_releases": changed,
        }