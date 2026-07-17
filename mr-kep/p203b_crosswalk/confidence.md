# P203B — Confidence Policy Application

> Existing Malt Radar confidence policy + P203 approved threshold.

| band | value | action |
|---|---|---|
| exact | 1.0 | auto-resolve |
| normalized | 0.9 | auto-resolve |
| ambiguous | 0.85 | auto-resolve (flagged) |
| below 0.7 | <0.7 | **manual review** (review queue) |

## Distribution observed
- Auto-resolved rows: exact=2197, normalized=2.
- Review-queued rows: 13 (all coverage-gap names).

## Nothing discarded
- Every unmatched name is preserved in `distillery_crosswalk_review` with reason + suggested_id=NULL.
- No silent drops; full audit trail via source/confidence/match_method columns.
