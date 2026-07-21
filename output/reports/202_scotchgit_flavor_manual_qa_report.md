# ScotchGit Flavor Manual QA Report

## Decision

- QA pack generation GO/NO-GO: **GO**
- Production import: **NO-GO**
- QA pack is for manual review only; no application integration or DB write was performed.

## Counts

- QA pack total rows: 255
- duplicate matched_master_whisky_id rows in QA pack: 0
- zero signal count in preview: 396
- region_only row count in preview: 431
- keyword_plus_region row count in preview: 96
- spicy coverage count in preview: 2

## Group Counts

- islay_smoky_expected: 30
- maritime_expected: 18
- sherry_expected: 30
- sweet_fruity_expected: 30
- zero_signal_review: 30
- high_signal_review: 30
- region_only_low_confidence_review: 30
- keyword_plus_region_review: 27
- suspicious_spicy_gap: 0
- random_sample: 30

## Spicy Coverage Warning

- Spicy coverage remains low at 2; no synthetic spicy signal was generated.

## Manual QA Production Import Criteria

- Keep production import NO-GO until manual reviewers mark acceptable rows in `manual_decision`.
- Region-only rows require independent approval before use as product flavor signals.
- Zero-signal rows should remain excluded unless keyword mapping is intentionally expanded.
- Suspicious spicy gap rows should be reviewed before changing keyword rules.
- Only `candidate_preview_only` rows may be considered, and approval must happen in a later gated phase.

## Output

- `C:/Users/eltun/Documents/malt radar/output/reports/201_scotchgit_flavor_manual_qa_pack.csv`
