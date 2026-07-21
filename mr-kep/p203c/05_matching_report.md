# P203C — 05 Matching Report

Matching pipeline (`WhiskyRegistryMatcher`, read-only on production.db) executed on all staged rows.
- Deterministic evidence_id: **YES** (`EDR-` + sha256(url|hash)[:16]).
- Idempotent (two passes byte-identical): **True**.
- Duplicate prevention: **True** (INSERT OR REPLACE, no duplicate rows).
- All staged rows currently `match_status=unmatched` — expected, since `whisky_raw_name` is a section title, not a whisky expression.
- No production.db write occurred (read-only join only).
