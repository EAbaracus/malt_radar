# Sprint 06 — Legacy CSV Candidate Resolution Report

> **READ-ONLY.** No production.db / knowledge.db writes. No schema changes. No promotion. Stop gate reached.

## 1. Input universe

- Candidate names extracted from 7 genuine CSV sources (Sprint 05): **1160** unique (1,546 mentions).
- This corrects Sprint 05's naive count (665): Sprint 05 matched only `whiskies.name`+`distilleries.name` with exact `.lower().strip()`, ignoring `original_name`, alias collapse, and the genuine-set double-count.

## 2. Deterministic matching against production.db

- **Matched (already exist):** 672 (57%)
- **Unmatched (true candidates):** 488 (42%)
- Match methods used (deterministic only):
  - `exact`: 402
  - `alias_collapse`: 249
  - `normalized`: 21

## 3. Classification (all candidates)

- Whisky: 810
- Distillery: 253
- Brand: 96
- Alias: 0
- Unknown: 1

## 4. True net-new whisky count

- **Confirmed new whiskies (unmatched + Whisky class): 213**
  - These carry age/ABV/distillery signals and are absent from production.db → ingestion-ready.

## 5. Metadata-only records

- **Brand-classified (no expression/age/ABV identity, metadata-only): 96**
  - These are brand/owner/catalog rows, not whisky expressions. Awaiting entity-type confirmation before intake.

## 6. Distillery candidates

- **New distillery candidates (unmatched + Distillery class): 178**
  - Absent from production.db `distilleries`; carry owner/region/founded/status metadata.

## 7. Duplicate records

- **Candidates present in 2+ distinct source files (cross-source duplicates): 343**
- Within-source exact duplicates were already collapsed in Part 1 (1,546 mentions → 1,160 unique).
- NO de-duplication or merge performed (read-only).

## 8. Ingestion-ready records (for a FUTURE intake sprint)

- **Total ingestion-ready: 391** = 213 new whiskies + 178 new distilleries.
- All require production.db seeding FIRST, then knowledge.db enrichment via the frozen source-scoped loader
  (FACT_{SOURCE_ID}_…, CIT_{SOURCE_ID}_…, BEGIN IMMEDIATE, NO INSERT OR IGNORE).

## 9. Unresolved

- **Unresolved queue: 97** (96 Brand + 1 Unknown) → `unresolved_candidates.csv`.
- 0 pure Alias-classified records (none flagged as alias-only in the source metadata).

## 10. Acceptance

- ✅ Read-only execution (no DB mutations)
- ✅ No schema modifications
- ✅ No promotion
- ✅ All 4 required CSVs + this report generated
- ✅ Deterministic matching only (exact / normalized / original_name / alias-collapse)

**STOP** — candidate set fully resolved. No CSV data ingested.