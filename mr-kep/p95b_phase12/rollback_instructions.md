# P95B Phase 12 — Rollback Instructions (if ever required)

**Current state:** PASS. production.db = `704fee10138560b18492557feb1bd97a4a8dac35256d5dbae57c6c5a607323a1`
(987 evidence rows, `vector_maritime` present). Rollback is **not** needed now, but
documented for safety per Phase E.

---

## Full rollback (restores pre-Phase-12 state)
```bash
cd "C:/Users/eltun/Documents/malt radar CLEAN"
cp "mr-kep/p95b_phase12/backups/production.db.pre_p95b_phase12.20260718_101917.bak" \
   "output/import/production.db"
```
Verity:
```python
import hashlib
print(hashlib.sha256(open("output/import/production.db","rb").read()).hexdigest())
# must equal: 8350fe9de2f1c73d9c4b6930bae607afe64696527910c2709b8b3a4a634c6a3a
```

## What rollback undoes
- Removes the `vector_maritime` column from `flavor_evidence`.
- Removes the 196 promoted evidence rows (`evidence_id` LIKE `P95B_%`).
- Restores `flavor_profiles` to its pre-state (no profiles were inserted, so unchanged).
- Restores legacy `vector_rich` (791 rows) and the 0-1 historical scale.

## Partial rollback (keep schema, remove only promoted data)
If you want to keep `vector_maritime` but remove the 196 promoted rows:
```sql
DELETE FROM flavor_evidence WHERE evidence_id LIKE 'P95B_%';
```
(This leaves the column; safe if downstream code already expects `vector_maritime`.)

## Guardrails
- The authorized script (`p95b_phase12_execute.py`) performs an **automatic full rollback**
  (restores from the backup) if ANY validation gate or the regression suite fails — it did
  not trigger because all gates passed.
- Never run `migration.sql` (P95B-FIX-02) separately — Phase B of the executor
  already applied the identical `ALTER`.
- Always re-run `PRAGMA integrity_check` and the P95B-FIX-02 regression
  (`pytest mr-kep/p95b_fix02/test_canonical_axes.py`) after any rollback.

## Audit artifacts
- `promotion_audit_log.json` — full before/after SHA, promoted counts, skipped reasons,
  validation summary, regression result.
- `backups/production.db.pre_p95b_phase12.20260718_101917.bak` — verified, SHA-matched.
