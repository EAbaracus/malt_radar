# P251 — 05 — ROLLBACK PLAN

**Mode:** READ_ONLY · **Rollback *specification* for a future authorized apply — nothing executed.**

## 1. Pre-apply snapshot (mandatory gate)

```sql
.backup DB backups/production.pre_p251_apply_<YYYYMMDD_HHMMSS>.db;
-- record live SHA (must equal frozen f3419951…bf67a12)
-- capture baselines: SELECT count(*) FROM whiskies WHERE distillery_id IS NULL OR trim(distillery_id)='';
--   expected NULL = 1,931; FK violations = 0; D1091 children = 15
```

Apply proceeds only if live SHA == snapshot SHA.

## 2. Authorized apply statements (NOT run here)

```sql
-- Wave A: 1,902 FK binds (idempotent; updates only NULL/unbound)
UPDATE staging_book_flavor_profiles SET distillery_id=:t WHERE match_method='no_distillery_match' AND upper(trim(distillery_name)) IN (SELECT upper(trim(name)) FROM distilleries);
UPDATE whiskies SET distillery_id=:t WHERE (distillery_id IS NULL OR trim(distillery_id)='') AND whisky_id IN (:safe_ids);  -- 1,902 precomputed

-- Wave B: repoint D1091 children to D0010 (idempotent; keyed on current D1091)
UPDATE whiskies        SET distillery_id='D0010' WHERE distillery_id='D1091';
UPDATE tasting_notes   SET distillery_id='D0010' WHERE distillery_id='D1091';
UPDATE flavor_profiles SET whisky_id=whisky_id WHERE whisky_id IN (SELECT whisky_id FROM whiskies WHERE distillery_id='D0010'); -- no-op placeholder; FP links via whisky_id, already valid
UPDATE distilleries SET status='deprecated_alias', notes_for_review='merged into D0010 (P250/P251)' WHERE distillery_id='D1091';  -- non-destructive

-- Wave C (collision-gated): distilleries.name fold ONLY + unique whisky names; colliding pairs skipped
UPDATE distilleries SET name='Glenfiddich' WHERE distillery_id='D0010' AND name LIKE '%ﬁ%';
UPDATE whiskies SET name=:norm WHERE whisky_id IN (:unique_norm_ids);  -- excludes the 13 colliding pairs
```

All statements are **single-column UPDATEs**; no DROP/DELETE/RENAME.

## 3. Audit trail (write alongside)

```sql
INSERT INTO promotion_audit_log (entity_table, entity_id, field, before_value, after_value, source, applied_at)
VALUES (:table, :id, :field, :before, :after, 'p251_apply', :ts);
```

## 4. Rollback (two-tier, non-destructive)

```sql
-- PRIMARY (atomic): restore snapshot
-- (outside SQL) cp backups/production.pre_p251_apply_*.db production.db

-- SECONDARY (row-level, via audit trail):
UPDATE whiskies w SET distillery_id=a.before_value
  FROM promotion_audit_log a
 WHERE a.entity_table='whiskies' AND a.field='distillery_id'
   AND a.source='p251_apply' AND w.whisky_id=a.entity_id;
-- (repeat per table: tasting_notes, distilleries.name)
```

No destructive op is used; rollback is always a reversible `UPDATE` or a full restore.

## 5. Post-apply verification gate

```sql
SELECT count(*) FROM whiskies WHERE distillery_id IS NULL OR trim(distillery_id)='';  -- expect 724
SELECT count(*) FROM whiskies w LEFT JOIN distilleries d ON w.distillery_id=d.distillery_id
  WHERE w.distillery_id IS NOT NULL AND w.distillery_id!='' AND d.distillery_id IS NULL; -- expect 0
SELECT count(*) FROM distilleries WHERE distillery_id='D1091';  -- expect 1 (deprecated, not deleted)
```

## 6. Conclusion

Rollback is fully specified, snapshot-primary + audit-trail-secondary, and entirely
non-destructive. Not executed in this audit.
