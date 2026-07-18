# P203C-FIX — 06 Matching Validation

Matching pipeline (`WhiskyRegistryMatcher`, read-only on production.db) executed per source.
- Deterministic evidence_id: **YES** (`EDR-` + sha256(url|hash)[:16]).
- Idempotent (two full passes byte-identical): **True**.
- Duplicate prevention: ON CONFLICT upsert, no duplicate rows.
- Canonical 7-axis vectors valid + bounded [0,1].

## Per-source match

| source | raw_name | match_status | matched_id |
|---|---|---|---|
| thewhiskyphiles | Glenmorangie 18 Year Old Signet Reserve | exact | W003214 |
| whiskymonster | Lagavulin 16 Year Old | manual_review | W001100 |
| thedramble | Clynelish 14 Year Old | manual_review | W000496 |
| whiskynotes_be | Ardbeg 10 Year Old | manual_review | W001152 |
| thewhiskeywash | Talisker 10 Year Old | manual_review | W000976 |
| wordsofwhisky | Highland Park 12 Year Old Viking Honour | exact | W003734 |

## Note
- Some resolve `exact` (Glenmorangie, Highland Park); others `manual_review` (fuzzy on age/expression) — all deterministic and reviewable. No production.db write.
