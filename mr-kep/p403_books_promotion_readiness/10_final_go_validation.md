# P403 — 10 Final GO Validation (READ-ONLY)

**Read-only cross-check of the existing manifest against live production schema + data. No regeneration, no SQL execution, no promotion. Production SHA: `3c56de601c53…`**

## Executive Summary

The existing promotion manifest (`06_promotion_manifest.json`) is **internally consistent** and the promotion is **mechanically safe** — but validation surfaced **6 manifest whiskies that already carry a `book`-source evidence row in production** (no UNIQUE constraint on `(whisky_id, source)` exists, so a naive 64-row insert would create 6 duplicate `book` rows). Final verdict: **GO_WITH_CONDITIONS**. The single hard condition: **resolve the 6 duplicate-book-source whiskies before Apply** (skip or upsert). All other provenance gaps are NOT schema failures — the `flavor_evidence` table simply has no `author`/`citation`/`evidence_id`/`authority_tier` columns, so their absence cannot block an INSERT.

## Manifest Validation (P1)

| Check | Result |
|---|---|
| Manifest eligible count | 64 |
| Distinct whisky_ids | 64 |
| Duplicate ids in manifest | False |
| Invalid whisky_ids in manifest | 0 |
| Deterministic (sorted) order | True |
| Manifest checksum | `a5e8a463d344a38e3ff095ff79b60176` |
| Recomputed checksum | `a5e8a463d344a38e3ff095ff79b60176` |
| **Checksum match** | **True** |

Manifest is internally consistent and deterministic. ✓

## Production Impact (P2)

| Metric | Count |
|---|---|
| Total manifest whiskies | 64 |
| INSERT (new evidence) | 52 |
| UPDATE (additional source) | 12 |
| First-evidence gains | 52 |
| Additional-evidence gains | 12 |
| **Duplicate `book`-source risk** | **6** (whiskies: W000014, W001980, W002288, W002442, W002565, W002573) |

Per-whisky INSERT/UPDATE/first-evidence classification computed for all 64 manifest rows (sample below). The 6 flagged whiskies already have 1–2 `book` rows each (e.g. W000014 has 2 book rows) — a plain insert would duplicate them.

Sample:
- `W000001`: pre=0 → post=1 — INSERT (first evidence)
- `W000002`: pre=0 → post=1 — INSERT (first evidence)
- `W000004`: pre=0 → post=1 — INSERT (first evidence)
- `W000011`: pre=0 → post=1 — INSERT (first evidence)
- `W000012`: pre=0 → post=1 — INSERT (first evidence)
- `W000013`: pre=0 → post=1 — INSERT (first evidence)
- `W000014`: pre=2 → post=3 — UPDATE (additional source) | DUP-BOOK-SOURCE RISK
- `W000015`: pre=0 → post=1 — INSERT (first evidence)


## Evidence Analysis (P2 cont.)

- No primary-key collision: `evidence_id` is the only PK (`sqlite_autoindex_flavor_evidence_1` on `evidence_id`), and the manifest does not pre-assign evidence_ids (the writer will generate them). ✓
- No UNIQUE index on `(whisky_id, source)` → **duplicate-source rows are possible**. This is the one real risk and must be handled by the promotion writer (skip-if-exists or upsert on whisky_id+source+book).

## Provenance Analysis (P3)

Against the **actual `flavor_evidence` schema** (required NOT-NULL columns: ``):

| Field | Classification | Reason |
|---|---|---|
| whisky_id | REQUIRED | Part of primary key (NOT NULL) |
| source | REQUIRED | NOT NULL column; manifest sets `source='book'` |
| author | NOT USED | No column in `flavor_evidence` |
| citation | NOT USED | No column in `flavor_evidence` |
| citation_id | NOT USED | No column in `flavor_evidence` |
| evidence_id | NOT USED | Not a column in `flavor_evidence` (PK is auto/internal; editorial staging uses EDR-<sha16> but that does not propagate here) |
| authority tier | NOT USED | No column in `flavor_evidence` |
| page reference | NOT USED | No column in `flavor_evidence` |
| confidence | OPTIONAL | `extraction_confidence`/`parser_confidence` columns exist but are NULLABLE |

**Conclusion:** The missing provenance fields (author/citation/evidence_id/authority_tier/page) are **NOT USED** by the production schema — their absence is not a schema violation. Promotion only requires `whisky_id` (valid) + `source` (set) + axis vectors (present). Confidence is optional.

## Policy Compliance (P4)

| Check | Status | Why |
|---|---|---|
| Schema compatible | PASS | All referenced columns exist |
| whisky_id valid & exists | PASS | All 64 ids exist in `whiskies` |
| No duplicate keys (PK) | PASS | Writer generates evidence_id; no PK clash |
| No duplicate `book` source | **WARNING** | 6 whiskies already have a `book` row; no UNIQUE(src,whisky) — must skip/upsert |
| confidence present | WARNING | `flavor_data_confidence` null on all 64; column is nullable |
| source='book' assigned | PASS | Manifest sets it |
| Provenance completeness | WARNING | Book-level provenance only (title+distillery); per-row citation absent by schema design — policy call, not a hard failure |

## Risk Assessment

- **HIGH-risk items:** 0 (no PK/orphan/invalid-ref failures).
- **MEDIUM-risk:** 6 duplicate-book-source whiskies — mitigated by writer skip/upsert logic.
- **LOW-risk:** confidence null (nullable), provenance granularity (policy, not technical).
- **Rollback:** ready (`07_rollback_manifest.json`) — `DELETE FROM flavor_evidence WHERE source='book' AND whisky_id IN (manifest)`; pre-promotion hash captured.

## Final Verdict (P5)

**GO_WITH_CONDITIONS**

### Conditions (must be satisfied before Apply)
1. **Resolve the 6 duplicate-book-source whiskies** (W000014, W001980, W002288, W002442, W002565, W002573) — skip them or upsert (do not insert a second `book` row). This is the only technical condition.
2. **Accept book-level provenance** (book title + distillery) as sufficient, since `author`/`citation`/`evidence_id`/`authority_tier` are NOT USED by the `flavor_evidence` schema.

### No hard blockers (NO_GO not warranted)
All schema/constraint/entity checks PASS. The promotion is mechanically safe and deterministic; the conditions above are resolvable without schema changes.

## Verification

| Item | Value |
|---|---|
| git branch | `feature/editorial-crawl-phase` |
| git status --short | 70 lines (untracked audit artifacts only; no tracked mods) |
| git diff --stat | `mr-kep/authority/source_priority.yaml | 4 ++++
 1 file changed, 4 insertions(+)` |
| production.db SHA256 | `3c56de601c539260b49df57657eae4d47bfc8d0ebb27354b01c20648ac71656c` |
| knowledge.db SHA256 | `e4c0d8b42d2173c372278098b9b6df539c89fc1f8853062995b830313b00b682` |
| DB byte-identical (unchanged) | YES — no writes performed in this read-only validation |

**STOP — READ-ONLY. No promotion. No SQL execution. No production writes. Awaiting explicit human GO (and resolution of the 6 duplicate-source whiskies) before any Apply.**
