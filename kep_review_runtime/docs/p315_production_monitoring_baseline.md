# Production Monitoring Baseline â€” P315

**Mode:** READ ONLY AUDIT ONLY Â· No writes Â· No migration Â· No promotion Â· No rollback Â· No commit/push/tag
**Date:** 2026-07-18

---

## 1. Production Health Check

| Check | Value | Baseline Status |
|---|---|---|
| `PRAGMA integrity_check` | `ok` | âœ… |
| `PRAGMA user_version` | `0` | âœ… |
| Total tables | `37` | âœ… |
| Total size on disk | 12,709,888 bytes | âœ… |
| SHA-256 (post-promotion) | `12d5c31907e38c31075ceaff13814bf9b54028f14ec4ca1a2d6a6211426d62b2` | **BASELINE** |

### Table Row Counts (baseline for drift detection)

| Table | Row count | Table | Row count |
|---|---|---|---|
| whiskies | 4,749 | distilleries | 2,144 |
| flavor_profiles | 3,468 | flavor_evidence | **990** |
| tasting_notes | **1,849** | brands | 471 |
| price_history | 1,327 | official_source_references | 96 |
| promotion_audit_log | **3** | review_actions | 6 |
| review_status_transitions | 7 | knowledge_guides | 50 |
| knowledge_regions | 23 | knowledge_glossary_terms | 50 |
| sqlite_sequence | 20 | staging_book_flavor_profiles | 2,577 |
| staging_flavor_profile_candidates | 650 | staging_flavor_profile_candidates_full | 6,133 |
| staging_manual_review_queue | 62 | staging_tasting_notes | 733 |
| staging_p6_flavor_profile_candidates | 17 | staging_notebooklm_flavor_profiles | 17 |
| staging_historical_menu_prices | 20 | staging_web_tasting_notes | 2 |
| entity_external_links | 0 | bottler_product_links | 0 |
| bottlers | 0 | companies | 0 |

*Counts with marked promotion contribution: flavor_evidence 989â†’990 (+1), tasting_notes 1848â†’1849 (+1), promotion_audit_log 2â†’3 (+1). All other tables unchanged.*

---

## 2. Promotion Drift Check

| Check | Manifest | Production | Match? |
|---|---|---|---|
| `promotion_id` | `PROMO-20260718-001` | `PROMO-20260718-001` (audit log) | âœ… |
| `evidence_id` | `EDR-b6108f7ac8d252af` | `EDR-b6108f7ac8d252af` (flavor_evidence) | âœ… |
| `whisky_id` | `W003571` (product) | `W003571` (production) | âœ… |
| Certification state | `APPROVED` | Not stored in DB â€” manifest only | âšª Read-only |
| Provenance state | `APPROVED` | Not stored in DB â€” manifest only | âšª Read-only |

**Drift: NONE DETECTED.** All promoted records remain present and unchanged since promotion.

---

## 3. Data Quality Scan

| Check | Result |
|---|---|
| Duplicate `evidence_id` values in flavor_evidence | âœ… **NONE** |
| flavor_evidence rows with axis > 1.0 | âœ… **0** (all valid) |
| Orphan tasting_notes (no matching flavor_evidence) | âœ… **0** |
| Missing required fields in promoted records | âœ… All fields populated |

---

## 4. Backup Health

| Check | Result |
|---|---|
| Backup file exists | âœ… `backups/production.pre_PROMO-20260718-001.20260718T235627_+0300.db` |
| SHA-256 unchanged since pre-promotion | âœ… `045ba814445f637c74c1732cc96550ec6ba9c2e0221c53b5b35a7e6bfa68f352` |
| Backup `PRAGMA integrity_check` | âœ… `ok` |
| Size | 12,709,888 bytes (identical to pre-promotion source) |
| Matches manifest target hash | âœ… `045ba814â€¦` = manifest `target.database.sha256` |

---

## 5. Audit Log Health

| Check | Result |
|---|---|
| `PROMO-20260718-001` exists in `promotion_audit_log` | âœ… |
| `promotion_status` | âœ… `SUCCESS` (unchanged) |
| Authorized by | âœ… `eltun` |
| Contradictory (FAILED) entries for this promotion | âœ… **NONE** |
| Total audit log entries | 3 (2 pre-existing + 1 from this promotion) |

---

## 6. Monitoring Baseline Summary

### Current Healthy State (for future drift comparison)

| Indicator | Baseline value |
|---|---|
| Production SHA-256 | `12d5c31907e38c31075ceaff13814bf9b54028f14ec4ca1a2d6a6211426d62b2` |
| Integrity check | `ok` |
| User version | `0` |
| flavor_evidence row count | `990` |
| tasting_notes row count | `1,849` |
| whiskies row count | `4,749` |
| promotion_audit_log count | `3` |
| EDR-b6108f7ac8d252af in flavor_evidence | âœ… Present |
| W003571 (Ardbeg 10) in whiskies | âœ… Present |
| Duplicate evidence_ids | 0 |
| Invalid flavor vectors (axis > 1.0) | 0 |
| Orphan tasting_notes | 0 |

### Expected drift indicators

| Event | Expected effect |
|---|---|
| New promotion | flavor_evidence, tasting_notes, promotion_audit_log counts increase |
| New whisky added | whiskies row count increases |
| Data correction | SHA-256 changes; specific table counts may change |
| Schema migration | user_version may change, tables may be added/removed |
| Backup creation | backup count increases; original backup hash unchanged |
| Unauthorized change | SHA-256 changes without corresponding audit log entry; orphan records may appear |

---

## Final Status

```
PRODUCTION:  HEALTHY
PROMOTION:   CLOSED
BACKUP:      PRESERVED & VERIFIED
MONITORING:  BASELINE ESTABLISHED
DRIFT:       NONE DETECTED

Next monitoring: compare current SHA-256, row counts, and
promoted evidence presence against this baseline. Any deviation
indicates drift requiring investigation.
```

**No writes performed. No migration. No promotion. No rollback.**
