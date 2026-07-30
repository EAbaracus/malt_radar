# Decision Matrix â€” P305

**Package:** P305 â€” Human Certification Decision Record Package
**Candidate:** `evidence_id = EDR-b6108f7ac8d252af`

| Decision | Impact | Risk | Required approval |
|---|---|---|---|
| Accept evidence | Allows promotion of candidate record | Low â€” evidence already present and confident (conf â‰¥ 0.70) | Reviewer "Accept evidence" checkbox â€” **[x] RECORDED (P306)** |
| Reject evidence | Discards candidate; no promotion | Medium â€” loss of a complete candidate; pipeline re-run needed if later wanted | Reviewer "Reject evidence" checkbox |
| Request additional evidence | Triggers re-extraction if needed | Lowâ€“Medium â€” delays resolution | Reviewer "Request additional evidence" checkbox |
| Promote authority tier | Elevates T2 evidence to T1 ceiling for identity fields | Medium â€” affects downstream authority standards; must be documented | Reviewer "Promote authority tier" + human GO â€” **[x] RECORDED (P306 + P303 GO)** |
| Keep HOLD | Maintains current state | None immediate â€” candidate stays unpromoted | Reviewer selects "Keep HOLD" |

---

**Final status:** APPR0VED Â· PROMOTED (T2â†’T1) Â· CONFIRMED LIVE IN PRODUCTION
_Decision boxes for this candidate are resolved per P306 (2026-07-18) and confirmed live per P303 (2026-07-25). References `output/meleklerinpayi_ze_audit/P303_COMMIT_RESULT.json`. No production.db write performed by this edit._
