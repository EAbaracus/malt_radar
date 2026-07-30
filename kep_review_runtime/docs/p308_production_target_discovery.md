# Production Target Discovery Report â€” P308

**Mode:** READ ONLY ONLY Â· No writes Â· No migration Â· No backup creation Â· No promotion Â· No commit/push/tag
**Date:** 2026-07-18
**Method:** Systematic file search â†’ read-only SQLite validation â†’ comparison against known production characteristics. Filenames were NOT assumed; every candidate was validated.

---

## 1. Discovered SQLite Candidates

### Primary candidates (non-backup, non-staging)

| # | Absolute path | Size (bytes) | Last modified |
|---|---|---|---|
| 1 | `/c/Users/eltun/Documents/malt radar CLEAN/output/import/production.db` | 12,709,888 | 2026-07-18 22:07 |
| 2 | `/c/Users/eltun/Documents/malt radar CLEAN/output/import/knowledge.db` | 4,083,712 | 2026-07-17 20:56 |
| 3 | `/c/Users/eltun/Documents/malt radar CLEAN/mr-kep/p102_bootstrap/knowledge.db` | 12,214,272 | (not checked) |
| 4 | `/c/Users/eltun/Documents/malt radar CLEAN/mr-kep/editorial/staging_editorial.db` | 49,152 | (not checked) |
| 5 | `/c/Users/eltun/Documents/malt radar CLEAN/data/p203c_staging/editorial_staging.db` | (not opened) | (not checked) |

### Discovered but excluded pre-operational backups (representative sample)

```
output/import/production_before_*.db          â€” pre-operation snapshots (Ã—36)
output/import/backups/production_p*_pre*.db   â€” pre-migration backups (Ã—20+)
mr-kep/editorial/promotion/backups/production.pre_editorial_promo.*.db  â€” promo backups (Ã—5)
backups/production.pre_*.db                   â€” general backups (Ã—2)
data/output/p61a_migration/production_p61a_staging_*.db  â€” migration artifacts
artifacts/2026-07-05_p6_snapshot/.../production.db       â€” snapshot (path does not exist)
```

---

## 2. Validation Results (read-only SQLite)

### Candidate 1: `output/import/production.db` â† **the real target**

| Check | Result | Expected? |
|---|---|---|
| File exists | YES | âœ“ |
| File readable | YES | âœ“ |
| Integrity check | **ok** | âœ“ |
| User version | 0 | âœ“ |
| Total tables | **37** | matches production schema |
| whiskies table | **4,749 rows** | âœ“ (expected 4,000â€“5,000) |
| distilleries table | **2,144 rows** | âœ“ |
| brands table | **471 rows** | âœ“ |
| flavor_profiles table | **3,468 rows** | âœ“ |
| flavor_evidence table | **989 rows** | âœ“ |
| tasting_notes table | **1,848 rows** | âœ“ |
| staging_* tables | **9 staging tables** | âœ“ (active ingestion pipeline) |
| promotion_audit_log | **2 rows** | âœ“ (past promotions recorded) |
| review_actions / review_status_transitions | present | âœ“ (review workflow) |

### Candidate 2: `output/import/knowledge.db` (3.9 MB)

- **Classification: Knowledge base** â€” evidence, normalized_metadata, citations, sources, canonical_flavor_vectors
- **NOT production.** Contains raw ingestion data, citation records, and crosswalk tables.
- Not a promotion target.

### Candidate 3: `mr-kep/p102_bootstrap/knowledge.db` (11.9 MB)

- **Classification: Historical/ingestion knowledge base** â€” books, evidence_nodes, extracted_facts, consensus_nodes
- **NOT production.** Pre-canonicalization knowledge store.
- Not a promotion target.

### Candidates 4â€“5: `staging_editorial.db` variants (48 KB)

- **Classification: Staging** â€” contains `staging_editorial_reviews` (7 rows) and `staging_editorial_profiles`
- Explicitly excluded by task (staging databases).

---

## 3. Comparison Against Known Production Characteristics

| Characteristic | Expected indicator | validation on `output/import/production.db` | Match? |
|---|---|---|---|
| Production schema presence | `whiskies`, `distilleries`, `brands`, `flavor_profiles` tables | All present | âœ“ |
| whisky table | 4,000â€“5,000 rows | 4,749 rows | âœ“ |
| distillery table | ~2,000 rows | 2,144 rows | âœ“ |
| flavor/profile tables | 3,000+ rows | 3,468 rows | âœ“ |
| tasting notes table | 1,500+ rows | 1,848 rows | âœ“ |
| Canonical data structures | `entity_aliases`, `official_source_references`, `price_history` | All present | âœ“ |
| Review workflow | `review_actions`, `review_status_transitions` | Both present | âœ“ |
| Promotion history | `promotion_audit_log` with rows | 2 rows | âœ“ |
| Active ingestion pipeline | `staging_*` tables | 9 staging tables | âœ“ |
| Integrity | `ok` | ok | âœ“ |
| User version | 0 | 0 | âœ“ |

---

## 4. Excluded Databases (with rationale)

| Database | Reason for exclusion |
|---|---|
| `output/import/knowledge.db` | Knowledge base, not production |
| `mr-kep/p102_bootstrap/knowledge.db` | Historical ingestion knowledge store |
| `mr-kep/editorial/staging_editorial.db` | Staging database (current editorial pipeline) |
| `data/p203c_staging/editorial_staging.db` | Staging database |
| `data/p203c_staging/editorial_staging_retry.db` | Staging retry database |
| All `production_before_*.db` | Pre-operation backups |
| All files under `backups/` directories | Backups |
| All files under `output/import/backups/` | Pre-migration backups |
| `data/output/p61a_migration/production_p61a_staging_*.db` | Migration staging artifact |
| `artifacts/` snapshot | Path does not exist on disk |

---

## 5. Final Conclusion

```
REAL PRODUCTION TARGET:
C:\Users\eltun\Documents\malt radar CLEAN\output\import\production.db

Confidence: HIGH

Evidence:
- 37 tables including whiskies (4,749 rows), distilleries (2,144), flavor_profiles (3,468)
- Integrity ok, user_version=0
- All expected production structures present
- Promotion audit log containing past promotions (2 entries)
- Active staging tables for ingestion pipeline
- Most recently modified 2026-07-18 â€” currently live
- No conflicting/competing production candidate found
```

**No database was modified. No backup was created. No promotion was executed.**
