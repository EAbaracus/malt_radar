# Promotion Authorization & Preflight Design â€” P307

**Mode:** DESIGN + READ-ONLY preparation Â· No promotion execution Â· No production writes Â· No staging mutation Â· No migration execution Â· No backup creation Â· No commit/push/tag
**Date:** 2026-07-18
**Purpose:** Define the gates, contracts, and forms required before the first real promotion can be authorized. **This document does NOT authorize promotion. No production path is invented.**

---

## 1. Current Certified State

### Candidate

| Attribute | Value |
|---|---|
| evidence_id | `EDR-b6108f7ac8d252af` |
| normalized_name | `ardbeg 10` |
| certification | **APPROVED** |
| provenance | **APPROVED** |
| reviewer | `eltun` |
| approval_date | `2026-07-18` |

### References

| Document | Path |
|---|---|
| Certification approval record | `kep_runtime/docs/p306_certification_approval_record.md` |
| Evidence bundle (expanded) | `kep_runtime/docs/certification_package/human_review_evidence_bundle.md` |
| Review bundle | `kep_runtime/docs/certification_package/review_bundle.md` |
| Diagnostic report | `kep_runtime/docs/certification_package/certification_diagnostic_report.md` |
| Manifest review | `kep_runtime/docs/p306_promotion_manifest_review.md` |

---

## 2. Promotion Preconditions (gates)

All gates must be satisfied before promotion execution. None are pre-filled.

- [ ] **Human promotion GO recorded** â€” explicit GO from an authorized reviewer
- [ ] **Production target path supplied** â€” absolute path to `production.db` (not guessed)
- [ ] **Target database validated** â€” file exists, readable, `integrity_check` passes
- [ ] **Schema compatibility verified** â€” target schema matches `staging_editorial_reviews` schema
- [ ] **Runtime version compatibility verified** â€” target schema_version = `1.0.0`, runtime_version = `0.1.0`
- [ ] **Backup procedure validated** â€” immutable pre-promotion copy created
- [ ] **Rollback procedure validated** â€” restore sequence tested and confirmed
- [ ] **Manifest sealed** â€” all manifest fields populated and signed
- [ ] **Checksums verified** â€” staging DB, content hash, backup all match manifest

---

## 3. Target Discovery Contract

### Required input (must be provided by an authorized operator â€” NOT discovered or guessed)

| Input | Description |
|---|---|
| Absolute production database path | e.g. `C:/Users/.../malt radar CLEAN/output/import/production.db` (operator-supplied) |
| Environment identifier | e.g. `production`, `staging`, `test` |
| Database checksum | SHA-256 of the production DB at discovery time |
| Schema version | Current `SCHEMA_VERSION` of the target |
| Runtime version | Current `RUNTIME_VERSION` of the runtime that will execute the promotion |

### Validation (to be run at preflight time)

- [ ] File exists at the supplied path
- [ ] File is readable (permissions check passed)
- [ ] `PRAGMA integrity_check` returns `ok`
- [ ] Expected schema detected (`staging_editorial_reviews`-compatible or `whiskies` table)
- [ ] Forbidden path rules respected (production path must NOT be under `mr-kep/fixtures/`, `mr-kep/acquisition/`, or any test/sample directory)

**Do NOT discover the target. Do NOT guess the path. The operator must supply it.**

---

## 4. Promotion Manifest Design (final sealed form)

A sealed promotion manifest MUST contain all of the following fields:

### Identity

| Field | Source |
|---|---|
| `promotion_id` | Generated at sealing time (e.g. `prom-YYYYMMDD-NNN`) |
| `evidence_ids` | `["EDR-b6108f7ac8d252af"]` (list of staged evidence) |
| `candidate_ids` | `["EDR-b6108f7ac8d252af"]` (alias â€” same as evidence_ids for single-candidate) |

### Runtime

| Field | Current value |
|---|---|
| `schema_version` | `1.0.0` |
| `runtime_version` | `0.1.0` |

### Source

| Field | Current value |
|---|---|
| `staging_db_hash` | `6e4ae12c27c343daabcabb315718634ba3a17ee5cd3689e1cdd30a4b15419217` |
| `content_hash` | `c0f37aa9251539ac7e82e19fa3611e1235e0489ea7db7b1da1e7ccd0a33b64ff` |
| `artifact_hashes` | (none â€” fixture is a pre-produced artifact; hash not independently recorded) |

### Certification

| Field | Value |
|---|---|
| `certification_state` | `APPROVED` |
| `provenance_state` | `APPROVED` |
| `approval_reference` | `kep_runtime/docs/p306_certification_approval_record.md` |

### Authorization (must be populated at sealing time â€” blank below)

| Field | Blank |
|---|---|
| `reviewer` | `[________________]` |
| `timestamp` | `[________________]` |
| `GO_reference` | `[________________]` |

---

## 5. Backup & Rollback Gate

### Backup requirements (executed BEFORE promotion, not now)

- An **immutable copy** of the target `production.db` must be created at a verifiable path.
- **SHA-256** computed before and after promotion to detect unintended changes to the backup.
- **Integrity verification** (`PRAGMA integrity_check`) run on the backup copy.

### Rollback requirements

- A written **restore procedure** that reverses the promotion by replacing `production.db` with the pre-promotion backup copy.
- `integrity_check` passed on the restored database.
- **Post-restore validation** confirming the candidate rows are no longer present in production.

### Current status

- Backup: **NOT YET CREATED** (requires target path)
- Rollback procedure: **NOT YET VALIDATED** (requires backup + target)

---

## 6. Human GO Form (template)

This form must be completed by an authorized reviewer at the moment of promotion authorization. Blank template below â€” nothing is pre-decided.

```
â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
PROMOTION AUTHORIZATION FORM
â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

Promotion decision:    [ ] GO    [ ] HOLD    [ ] REJECT

Reviewer:              ____________________________
Date:                  ____________________________
Target:                ____________________________
Manifest hash:         ____________________________
Backup confirmed:      [ ] Yes   [ ] No
Rollback confirmed:    [ ] Yes   [ ] No
Justification:
____________________________
____________________________
____________________________

â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
```

---

## 7. Risk Register

| ID | Risk | Severity | Mitigation | Blocking condition |
|---|---|---|---|---|
| R1 | **Wrong production target** â€” operator supplies incorrect path, promotion writes to wrong database | **High** | Target path must be validated by a second operator; path logged in manifest; `integrity_check` before and after | Target path not supplied or validation fails |
| R2 | **Incomplete manifest** â€” required fields missing (GO reference, backup hash, target) | **High** | Manifest schema validation at sealing time; automated field-required check | Any required field blank |
| R3 | **Certification mismatch** â€” target schema version differs from manifest `schema_version` | **Medium** | Verify target's `PRAGMA user_version` matches `1.0.0`; abort on mismatch | `PRAGMA user_version` â‰  `1.0.0` |
| R4 | **Backup failure** â€” pre-promotion backup fails (disk full, permission denied, path invalid) | **High** | Test write permission before promotion; validate backup SHA-256 before proceeding | Backup not created or checksum mismatch |
| R5 | **Rollback failure** â€” restore procedure fails (backup corrupted, wrong copy restored) | **High** | Regular backup integrity checks; maintain at least two independent backup copies | Backup `integrity_check` fails |
| R6 | **Unauthorized promotion** â€” promotion executed without valid human GO | **Critical** | Enforce multi-step gate: sealed manifest + explicit GO form + second operator confirmation | GO form not signed or GO reference blank |

---

## 8. Final Status

```
CERTIFICATION:    APPROVED
PROMOTION:       NOT AUTHORIZED
PRODUCTION:      UNTOUCHED

WAITING FOR:
- target discovery (operator must supply production database path)
- sealed manifest (all fields populated, GO reference signed)
- preflight validation (integrity_check, schema compatibility, backup)
- explicit promotion GO (form completed and signed)
```

**No promotion is authorized. No production path has been discovered or guessed. No backup has been created. This document defines the gate only.**
