# Batch Certification Decision Record â€” P319

**Mode:** DOCUMENTATION ONLY Â· No database writes Â· No staging mutation Â· No production mutation Â· No promotion Â· No commit/push/tag
**Date:** 2026-07-18
**Status:** PENDING HUMAN DECISION

---

## 1. Batch Identity

| Field | Value |
|---|---|
| `batch_id` | `PROMO-BATCH-20260718-001` |
| Candidate count | 4 |
| Evidence IDs | `EDR-0645f7a10c3c59c1`, `EDR-39d77abca9a6375e`, `EDR-63a322317c787409`, `EDR-9949a1899234acde` |
| Production IDs | `W001152`, `W000496`, `W000976`, `W001100` |
| Batch manifest ref | `kep_runtime/docs/p318_batch_certification_review_package.md` |
| Precedent | `PROMO-20260718-001` (single candidate ardbeg 10 â†’ W003571) |

---

## 2. Candidate Decisions

### Candidate A: Ardbeg 10 Year Old

**Diagnosis:**

| Check | Current state | Required action |
|---|---|---|
| **Match** | `manual_review` â†’ `W001152` (ardbeg 10yo) | Human acceptance of exact match |
| **Provenance** | `staging_unverified` | Human ratification |
| **Certification** | `HOLD` (T2 on T1_ceiling identity fields) | Human approval per P306 precedent |

**Options:**

| Choice | Impact |
|---|---|
| **Accept all** â€” exact match, ratify provenance, certify APPROVED | âœ… Candidate promoted in next batch execution |
| **Accept match, hold certification** â€” match accepted but needs more evidence review | â¸ Batch proceeds without this candidate |
| **Reject** â€” candidate excluded from batch | âŒ Flavor evidence not promoted; can be revisited later |

| Decision field | Decision |
|---|---|
| Match accepted? | **`__PENDING__`** |
| Provenance ratified? | **`__PENDING__`** |
| Certification approved? | **`__PENDING__`** |

**Justification:**
> *`__(reviewer to fill)__`*

---

### Candidate B: Clynelish 14 Year Old

**Diagnosis:**

| Check | Current state | Required action |
|---|---|---|
| **Match** | `manual_review` â†’ `W000496` (clynelish 14yo) | Human acceptance of exact match |
| **Provenance** | `staging_unverified` | Human ratification |
| **Certification** | `HOLD` (T2 on T1_ceiling identity fields) | Human approval per P306 precedent |

**Options:**

| Choice | Impact |
|---|---|
| **Accept all** | âœ… Promoted |
| **Accept match, hold** | â¸ Not promoted |
| **Reject** | âŒ Excluded |

| Decision field | Decision |
|---|---|
| Match accepted? | **`__PENDING__`** |
| Provenance ratified? | **`__PENDING__`** |
| Certification approved? | **`__PENDING__`** |

**Justification:**
> *`__(reviewer to fill)__`*

---

### Candidate C: Talisker 10 Year Old

**Diagnosis:**

| Check | Current state | Required action |
|---|---|---|
| **Match** | `manual_review` â†’ `W000976` (talisker 10yo) | Human acceptance of exact match |
| **Provenance** | `staging_unverified` | Human ratification |
| **Certification** | `HOLD` (T2 on T1_ceiling identity fields) | Human approval per P306 precedent |

**Options:**

| Choice | Impact |
|---|---|
| **Accept all** | âœ… Promoted |
| **Accept match, hold** | â¸ Not promoted |
| **Reject** | âŒ Excluded |

| Decision field | Decision |
|---|---|
| Match accepted? | **`__PENDING__`** |
| Provenance ratified? | **`__PENDING__`** |
| Certification approved? | **`__PENDING__`** |

**Justification:**
> *`__(reviewer to fill)__`*

---

### Candidate D: Lagavulin 16 Year Old

**Diagnosis:**

| Check | Current state | Required action |
|---|---|---|
| **Match** | `manual_review` â†’ `W001100` (lagavulin 16yo) | Human acceptance of exact match |
| **Provenance** | `staging_unverified` | Human ratification |
| **Certification** | `HOLD` (T2 on T1_ceiling identity fields) | Human approval per P306 precedent |

**Options:**

| Choice | Impact |
|---|---|
| **Accept all** | âœ… Promoted |
| **Accept match, hold** | â¸ Not promoted |
| **Reject** | âŒ Excluded |

| Decision field | Decision |
|---|---|
| Match accepted? | **`__PENDING__`** |
| Provenance ratified? | **`__PENDING__`** |
| Certification approved? | **`__PENDING__`** |

**Justification:**
> *`__(reviewer to fill)__`*

---

## 3. Batch Authorization

| Field | Value |
|---|---|
| Batch decision | **`__PENDING__`** (APPROVE / APPROVE_WITH_EXCLUSIONS / REJECT) |
| Authorized by | **`__PENDING__`** |
| GO reference | **`__PENDING__`** |
| Approval scope | **`__PENDING__`** (ALL / SELECTED â†’ list evidence IDs) |

### Exclusion list (if APPROVE_WITH_EXCLUSIONS)

| Evidence ID | Reason |
|---|---|
| `__` | `__` |
| `__` | `__` |

---

## 4. Risk Acknowledgement

| Risk | Acknowledgement |
|---|---|
| **Exact match accepted** â€” all 4 candidates' raw_names map cleanly to production whisky IDs. Normalized names match by age, distillery, region. No known conflicts. | **`__PENDING__`** |
| **Source evidence reviewed** â€” all 4 candidates from distinct external sources (`whiskynotes_be`, `thedramble`, `thewhiskeywash`, `whiskymonster`). All extract via heuristic method with confidence 0.85. None has conflicting evidence. | **`__PENDING__`** |
| **Rollback available** â€” pre-promotion backup at `backups/production.pre_PROMO-20260718-001.20260718T235627_+0300.db` (SHA-256: `045ba814â€¦`, integrity=ok). Batch will create a new immutable backup before execution. | **`__PENDING__`** |
| **Promotion remains separate step** â€” this decision record only certifies the candidates. Actual batch promotion execution requires a separate GO (P312 backup â†’ P313 execution). This document does NOT trigger promotion. | **`__PENDING__`** |

---

## Execution Plan (post-approval)

```
1. Update staging: match_status=exact for all 4 candidates
2. Update staging: provenance_state=APPROVED for all 4
3. Generate batch manifest PROMO-BATCH-20260718-001.yaml
4. Pre-promotion immutable backup (P312 pattern)
5. Execute batch promotion (P313 pattern, single transaction)
6. Post-promotion validation (P314 pattern)
7. Update monitoring baseline (P315 update)
```

---

## Final Status

```
BATCH:     PENDING HUMAN DECISION
PRODUCTION: UNCHANGED

All 4 candidates await reviewer decision.
Diagnostic information provided per P305.7 standard.
```

**No database writes. No staging mutation. No production mutation. No promotion. No commit/push/tag.**
