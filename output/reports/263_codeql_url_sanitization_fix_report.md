# CodeQL URL Sanitization Fix Report

## Issue Addressed
- **CodeQL High Vulnerability**: Incomplete URL Substring Sanitization.
- **Affected Files**:
  - `scripts/tasting_notes/fetch_web_tasting_note_snapshots.py`
  - `scripts/tasting_notes/discover_real_web_tasting_note_sources.py`

## Solution Implemented
- Created `url_safety.py` utility which uses `urllib.parse.urlparse` for secure scheme validation (HTTP/HTTPS only) and hostname extraction.
- Replaced naive string matching (`domain in url`) with a strict list-based matching rule using parsed properties (`host == domain or host.endswith("." + domain)`).
- Blocked embedded credentials/userinfo (`username`, `password`) in the URL parsing.
- Added test coverage in `tests/test_tasting_note_url_safety.py` for common SSRF/Open Redirect evasion techniques (query string injection, prefix/suffix spoofing, non-HTTP schemes).
