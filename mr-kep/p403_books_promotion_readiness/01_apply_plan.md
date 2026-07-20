# P404 — 01 Apply Plan

**Idempotent upsert of the EXISTING promotion manifest (`06_promotion_manifest.json`) into `production.db`. No manifest regeneration, no schema change, no re-audit.**

## Promotion Logic (per manifest entry)
```
FOR each whisky_id in manifest:
  IF (whisky_id, source='book') EXISTS:
       DELETE any EXTRA book rows (enforce <=1)
       UPDATE the kept row's axis vectors  (only if values differ)
  ELSE:
       INSERT exactly one new book row  (deterministic evidence_id = EVD-<sha16 of whisky|book>)
```
Final state guarantees **at most ONE book-source evidence row per whisky**.

## Required validations (pre-apply) — all PASS
| Check | Result |
|---|---|
| Manifest checksum match | True (`a5e8a463d344a38e3ff095ff79b60176`) |
| 64 distinct whiskies | True (distinct=64) |
| No invalid whisky_id | True |
| Production hashes captured | True |
| No duplicate in manifest | True |
| All manifest ids exist in prod | True |

## Target
- Database: `output/import/production.db` ONLY
- Table: `flavor_evidence` (columns `whisky_id`, `source`, `vector_smoky…vector_maritime`, `extraction_timestamp`)
- Evidence source: `book`
- No other table touched (no `flavor_profiles`, no `canonical_flavor_vectors`).
