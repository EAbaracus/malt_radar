# Promotion Manifest Review â€” P306

**Date:** 2026-07-18
**Purpose:** Document the promotion manifest fields for the approved certification record. **No promotion has been executed. No production target is set.**

---

## Manifest Fields

| Field | Value |
|---|---|
| promotion_id | `p306-2026-07-18-001` |
| evidence_ids | `["EDR-b6108f7ac8d252af"]` |
| candidate | `ardbeg 10` |
| source staging database | `mr-kep/editorial/staging_editorial.db` |
| schema_version | `1.0.0` (from `certification_engine/__init__.py` `SCHEMA_VERSION`) |
| runtime_version | `0.1.0` (from `kep_runtime/runtime/version.py` `RUNTIME_VERSION`) |
| staging DB checksum (SHA-256) | `6e4ae12c27c343daabcabb315718634ba3a17ee5cd3689e1cdd30a4b15419217` |
| candidate content hash | `c0f37aa9251539ac7e82e19fa3611e1235e0489ea7db7b1da1e7ccd0a33b64ff` |
| certification_state | `APPROVED` |
| provenance_state | `APPROVED` |
| authority decision | `T2_expert accepted` |
| human approval reference | `kep_runtime/docs/p306_certification_approval_record.md` |
| target | `[none â€” promotion not executed]` |
| reviewer | `eltun` |

---

## Validation Results

| Check | Result |
|---|---|
| Required fields present | YES â€” all manifest fields documented |
| Checksums match staging DB | YES â€” `6e4ae12câ€¦` verified read-only |
| Candidate matches staging DB | YES â€” `evidence_id = EDR-b6108f7ac8d252af`, `normalized_name = ardbeg 10` confirmed |
| No production target included | YES â€” target field set to `[none]` |
| No promotion executed | YES â€” this is a documentation record only; no `promote()` or production write was performed |
| No staging data mutated | YES â€” staging_editorial.db read-only verification confirms `HOLD` / `staging_unverified` unchanged |

---

## Promotion Prerequisites (remaining)

- [x] Evidence bundle reviewed (P305.5 + P305.6)
- [x] Certification approval recorded (this document)
- [x] T2 authority accepted
- [x] Provenance ratified
- [x] Reviewer identity recorded (eltun, 2026-07-18)
- [ ] Promotion manifest sealed (unsigned â€” awaiting final GO)
- [ ] Target production path populated (currently `[none]`)
- [ ] Human promotion GO executed (not yet â€” this is preparation only)
- [ ] Pre-promotion production backup verified
- [ ] Rollback path confirmed

---

## Production Isolation

- `output/production.db` does not exist on disk â€” never opened
- No promotion code path was triggered
- No stagingâ†’production write was attempted
- No commit/push/tag were performed
