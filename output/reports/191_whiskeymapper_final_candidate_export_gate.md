# Whiskey Mapper Final Candidate Export Gate

## Safety
- Production DB write: NO
- Malt Radar master CSV modified: NO
- Whiskey Mapper raw data modified: NO
- Outputs are candidate/QA/gap exports only.

## Inputs
- Match candidates: `data\output\whiskeymapper_malt_radar_match_candidates.csv`
- Rescue candidates: `data\output\whiskeymapper_no_match_rescue_candidates.csv`

## Source Counts
- Total match rows: 514
- HIGH: 362
- REVIEW: 94
- NO_MATCH: 58
- RESCUE_REVIEW: 32
- KEEP_NO_MATCH: 26

## Final Gate Outputs
- Import candidates HIGH only: 362 -> `data\output\whiskeymapper_final_import_candidates_high_only.csv`
- Manual QA queue REVIEW + RESCUE_REVIEW: 126 -> `data\output\whiskeymapper_final_manual_qa_queue.csv`
- Gap / keep no match candidates: 26 -> `data\output\whiskeymapper_final_gap_candidates.csv`

## Gate Decision
- HIGH rows may be considered for future import after final spot-check.
- REVIEW and RESCUE_REVIEW rows require manual approval.
- KEEP_NO_MATCH rows must not be imported.
- Production DB write remains blocked.

## Manual QA Risk Notes
- Same-brand but different age/edition rows remain risky.
- Cross-brand rows are blocked by rescue guard.
- Encoding artifacts should be cleaned before final human review display.
