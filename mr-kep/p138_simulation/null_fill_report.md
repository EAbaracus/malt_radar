# P138 — NULL Fill Report

- doc_version: P138-1
- date_utc: 2026-07-17
- mode: READ-ONLY simulation. production.db NOT modified.
- source: promotion_diff.csv (1,233 rows), action column = NULL_FILL.

## Summary
| field | column | rows | production before | proposed (smws) | confidence |
|---|---|---|---|---|---|
| cask_type | cask_type | 627 | NULL | refill / butt ; sherry butt / etc. | 0.95 |
| region | region | 531 | NULL | Highland / Islay / Speyside / … | 0.95 |

- **NULL_FILL total = 1,158** (627 + 531).
- Every NULL_FILL fills an empty production value from SMWS canonical metadata.
- All rows carry source_id = `smws`, confidence = 0.95, a valid `citation_id`,
  and a unique `dedupe_key` (0 duplicates).

## What a NULL_FILL means
- APPEND field (cask_type), current NULL → proposed written. Additive, safe.
- REPLACE field (region), current NULL → proposed written after normalization. Safe.
- No existing production value is touched or overwritten.

## Evidence integrity (per row)
- citation_id resolves in knowledge.db citations table (verified in P137B).
- provenance: source_id = smws (P137A D2 canonical).
- confidence chain preserved (0.95 → all HIGH).

## Sample (verbatim from promotion_diff.csv)
```
003ad896-…,cask_type,cask_type,,refill,APPEND,APPEND,0.95,CIT_…,smws,…,fill_null
003ad896-…,region,region,,Highland,APPLY,REPLACE,0.95,CIT_…,smws,…,fill_null
```

## Coverage gain if applied (from P137B coverage_delta.csv)
- cask_type: 0 → 627 (Δ +627)
- region: 75 → 606 (Δ +531)  [the 75 existing already present, 531 new fills]

## Conclusion
1,158 NULL_FILL rows are safe, additive, fully traceable promotions. They are the
entire "promotable" set — no OVERWRITE/CONFLICT/SKIP exists.
