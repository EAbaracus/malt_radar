# Batch Promotion Execution Report â€” PROMO-BATCH-20260718-001

**Mode:** AUTHORIZED WRITE EXECUTION
**Date:** 2026-07-18

---

## 1. Pre-Execution

| Check | Status |
|---|---|
| Staging update: match_status=exact for 3 candidates | âœ… |
| Staging update: provenance=APPROVED for 3 candidates | âœ… |
| Batch manifest generated | âœ… `manifest_PROMO-BATCH-20260718-001.yaml` |
| Dry-run: 3 accepted, 0 unexpected rejections | âœ… |
| Pre-promotion backup | âœ… `backups/production.pre_PROMO-BATCH-20260718-001.20260718T235627_+0300.db` |
| Backup SHA-256 matches source | âœ… `12d5c319â€¦` |
| Backup integrity_check | âœ… `ok` |

## 2. Execution

### Write batch 1: flavor_evidence (via EditorialPromotionWriter)

| evidence_id | whisky_id | source | Status |
|---|---|---|---|
| `EDR-0645f7a10c3c59c1` | `W001152` (ardbeg 10yo) | editorial | âœ… INSERT |
| `EDR-63a322317c787409` | `W000976` (talisker 10yo) | editorial | âœ… INSERT |
| `EDR-9949a1899234acde` | `W001100` (lagavulin 16yo) | editorial | âœ… INSERT |

### Write batch 2: tasting_notes

| whisky_id | normalized_name | Status |
|---|---|---|
| `W001152` | ardbeg 10 year old | âœ… INSERT |
| `W000976` | talisker 10 year old | âœ… INSERT |
| `W001100` | lagavulin 16 year old | âœ… INSERT |

### Write batch 3: promotion_audit_log

| promotion_id | status | promoted_by |
|---|---|---|
| `PROMO-BATCH-20260718-001` | SUCCESS | eltun |

### Excluded candidate

| evidence_id | Reason |
|---|---|
| `EDR-39d77abca9a6375e` (Clynelish 14yo) | Match status `manual_review`, provenance `HOLD` â€” awaiting decision |

## 3. Post-Execution Validation

| Check | Result |
|---|---|
| `PRAGMA integrity_check` | âœ… `ok` |
| Pre-promotion SHA-256 | `12d5c31907e38c31075ceaff13814bf9b54028f14ec4ca1a2d6a6211426d62b2` |
| Post-promotion SHA-256 | `cd87bb98316fbef247df8da3cbd987e11d50591cc79079d5e4392a70dfd77e75` |
| Change expected | âœ… Yes (3 flavor_evidence + 3 tasting_notes + 1 audit_log) |
| flavor_evidence count | 990 â†’ **993** (+3) |
| tasting_notes count | 1,849 â†’ **1,852** (+3) |
| promotion_audit_log count | 3 â†’ **4** (+1) |
| whiskies count | 4,749 (unchanged) |
| Rollback triggered | âŒ Not needed |

## 4. Rollback Available

| Backup | Path | SHA-256 | Integrity |
|---|---|---|---|
| Pre-batch | `backups/production.pre_PROMO-BATCH-20260718-001.20260718T235627_+0300.db` | `12d5c319â€¦` | âœ… ok |
| Pre-P313 | `backups/production.pre_PROMO-20260718-001.20260718T235627_+0300.db` | `045ba814â€¦` | âœ… ok |

---

## Final Status

```
PROMOTED: 3 candidates
  - Ardbeg 10yo      (W001152) â€” flavor_evidence + tasting_notes
  - Talisker 10yo    (W000976) â€” flavor_evidence + tasting_notes
  - Lagavulin 16yo   (W001100) â€” flavor_evidence + tasting_notes

HELD: 1 candidate
  - Clynelish 14yo   (W000496) â€” awaiting decision

PRODUCTION: VALIDATED
BACKUP: PRESERVED
```

**No commit/push/tag executed.**
