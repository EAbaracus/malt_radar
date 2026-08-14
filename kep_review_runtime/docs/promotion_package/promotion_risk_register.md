# Promotion Risk Register

**Package:** P303 â€” Promotion Decision Package (DOCUMENTATION ONLY)
**Scope:** Risks associated with promoting the P301 staging candidate to production.
**Severity scale:** Low / Medium / High. Mitigations listed per risk.

---

## R1 â€” Incorrect promotion

- **Severity:** High
- **Description:** Staging data promoted without a sealed manifest or valid human GO, causing unverified rows to enter production.
- **Mitigation:** Enforce a hard gate â€” promotion executes only with a sealed manifest (`promotion_manifest_spec.md`) AND an explicit human `GO`. Fail-closed otherwise.

## R2 â€” Incomplete evidence

- **Severity:** Medium
- **Description:** Candidate `EDR-b6108f7ac8d252af` carries certification `HOLD`; evidence may be insufficient for a clean certification.
- **Mitigation:** Block promotion until certification reaches `CLEAN`. Reviewer must confirm evidence completeness against the source fixture.

## R3 â€” Duplicate records

- **Severity:** Medium
- **Description:** A near-duplicate whisky entry already in production could create a second unmerged record.
- **Mitigation:** `SemanticDeduplicator` reported `duplicate=False` at staging time; re-run dedup against the live production set immediately before promotion and require `match_status` resolution.

## R4 â€” Schema mismatch

- **Severity:** Medium
- **Description:** Runtime/schema version drift between staging write time and promotion time could corrupt column mapping.
- **Mitigation:** Record `SCHEMA_VERSION=1.0.0` and `RUNTIME_VERSION=0.1.0` in the manifest; promotion must abort if the live schema/user_version differs. Verify staging DB SHA-256 (`6e4ae12câ€¦`) at promotion time.

## R5 â€” Rollback failure

- **Severity:** High
- **Description:** If promotion is faulty, an unavailable or corrupt backup prevents restoring the prior production state.
- **Mitigation:** Require a verified, checksummed pre-promotion backup and a tested restore procedure before any GO. Confirm rollback path exists prior to approval.

---

_No promotion has occurred. All risks are pre-emptive; mitigations are control requirements, not post-incident actions._
