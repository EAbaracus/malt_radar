# Reviewer Checklist

**Package:** P303 â€” Promotion Decision Package
**Candidate:** `evidence_id = EDR-b6108f7ac8d252af` (`normalized_name = "ardbeg 10"`)
**Status:** All items unchecked â€” pending human review. No item may be pre-filled.

---

- [ ] Evidence reviewed
- [ ] Provenance acceptable
- [ ] Flavor vector validated
- [ ] Duplicate risk checked
- [ ] Certification passed
- [ ] Rollback available
- [ ] Human approval recorded

---

## Notes for the reviewer

- **Evidence reviewed** â€” confirm the 10 extraction-execution evidence records and the source fixture are genuine and non-fabricated.
- **Provenance acceptable** â€” current `provenance_state = staging_unverified`; must be ratified before approval.
- **Flavor vector validated** â€” 7 canonical axes present and in [0,1]; spot-check against source.
- **Duplicate risk checked** â€” `SemanticDeduplicator` reported `duplicate=False`; re-confirm against current production.
- **Certification passed** â€” currently **HOLD**, not CLEAN; must be resolved first.
- **Rollback available** â€” confirm a verified backup/pre-promotion checkpoint exists before GO.
- **Human approval recorded** â€” explicit GO required; absent at time of writing.

_Record your decision in `promotion_review.md` â†’ Approval Decision Field._
