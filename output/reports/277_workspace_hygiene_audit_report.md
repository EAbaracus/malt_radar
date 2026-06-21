# 277 Workspace Hygiene Audit Report

## Overview
- modified tracked dosyalar: 5
- untracked source files: 15
- untracked generated/stale outputs: 0
- archive candidates: 3
- delete candidates: 4
- review required: 4
- keep tracked now: 2
- keep untracked for next phase: 9

## Findings grouped by Recommended Action

### DELETE_CANDIDATE
- `check_indexes.py` (??) - Temporary diagnostic scripts
- `check_table.py` (??) - Temporary diagnostic scripts
- `check_whiskies.py` (??) - Temporary diagnostic scripts
- `erseltunDocumentsmalt radar\357\200\242` (??) - Garbage/corrupted path artifact

### ARCHIVE_CANDIDATE
- `data/output/web_tasting_note_real_source_candidates.csv` (M) - Modified pipeline output, should be archived
- `data/output/web_tasting_note_real_source_manual_review.csv` (M) - Modified pipeline output, should be archived
- `data/output/web_tasting_note_snapshots_index.csv` (M) - Modified pipeline output, should be archived

### KEEP_TRACKED_NOW
- `output/reports/216_real_web_source_discovery_report.md` (M) - Pipeline reports should generally be committed
- `output/reports/219_web_tasting_note_real_snapshot_report.md` (M) - Pipeline reports should generally be committed

### KEEP_UNTRACKED_FOR_NEXT_PHASE
- `scripts/tasting_notes/apply_staging_tasting_notes.py` (??) - Active pipeline scripts waiting to be reviewed/committed
- `scripts/tasting_notes/audit_uploaded_production_tasting_note_quality.py` (??) - Active pipeline scripts waiting to be reviewed/committed
- `scripts/tasting_notes/diagnose_uploaded_notes_flavor_extraction.py` (??) - Active pipeline scripts waiting to be reviewed/committed
- `scripts/tasting_notes/dryrun_apply_staging_tasting_notes.py` (??) - Active pipeline scripts waiting to be reviewed/committed
- `scripts/tasting_notes/extract_tasting_notes_from_seed_candidates.py` (??) - Active pipeline scripts waiting to be reviewed/committed
- `scripts/tasting_notes/generate_flavor_profile_preview_from_uploaded_notes.py` (??) - Active pipeline scripts waiting to be reviewed/committed
- `scripts/tasting_notes/recover_scotchgit_text_snapshots.py` (??) - Active pipeline scripts waiting to be reviewed/committed
- `scripts/tasting_notes/seed_existing_real_tasting_note_sources.py` (??) - Active pipeline scripts waiting to be reviewed/committed
- `scripts/tasting_notes/validate_tasting_note_extraction_preview.py` (??) - Active pipeline scripts waiting to be reviewed/committed

### REVIEW_REQUIRED
- `frontend/lib/core/widgets/` (??) - Frontend files should be reviewed before automated clean
- `frontend/lib/features/whisky/data/dto/` (??) - Frontend files should be reviewed before automated clean
- `frontend/lib/features/whisky/data/repositories/db_whisky_repository_impl.dart` (??) - Frontend files should be reviewed before automated clean
- `scripts/qa/audit_workspace_hygiene.py` (??) - Unclassified untracked file

## Next Safe Cleanup Phase Recommendation
1. Delete garbage paths (corrupted files)
2. Delete temporary diag scripts (`check_*.py`)
3. Archive modified CSV pipeline outputs
4. Review and selectively commit active `scripts/tasting_notes/` scripts
5. Keep frontend files un-touched until a frontend-specific phase
