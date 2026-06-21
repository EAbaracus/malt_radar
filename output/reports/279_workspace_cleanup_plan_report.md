# 279 Workspace Cleanup Plan Report

## Overview
- DELETE Candidates: 4
- ARCHIVE/RESTORE Candidates: 8
- REVIEW Required: 3
- KEEP for next phase: 7

## Delete Plan
- `check_indexes.py` -> `rm 'check_indexes.py'`
- `check_table.py` -> `rm 'check_table.py'`
- `check_whiskies.py` -> `rm 'check_whiskies.py'`
- `erseltunDocumentsmalt radar\357\200\242` -> `rm -rf 'erseltunDocumentsmalt radar\357\200\242'`

## Archive/Restore Plan
- `data/output/web_tasting_note_real_source_candidates.csv` -> `git restore 'data/output/web_tasting_note_real_source_candidates.csv'`
- `data/output/web_tasting_note_real_source_manual_review.csv` -> `git restore 'data/output/web_tasting_note_real_source_manual_review.csv'`
- `data/output/web_tasting_note_snapshots_index.csv` -> `git restore 'data/output/web_tasting_note_snapshots_index.csv'`
- `output/reports/216_real_web_source_discovery_report.md` -> `git restore 'output/reports/216_real_web_source_discovery_report.md'`
- `output/reports/219_web_tasting_note_real_snapshot_report.md` -> `git restore 'output/reports/219_web_tasting_note_real_snapshot_report.md'`
- `scripts/tasting_notes/audit_uploaded_production_tasting_note_quality.py` -> `mv 'scripts/tasting_notes/audit_uploaded_production_tasting_note_quality.py' data/output/archive/`
- `scripts/tasting_notes/diagnose_uploaded_notes_flavor_extraction.py` -> `mv 'scripts/tasting_notes/diagnose_uploaded_notes_flavor_extraction.py' data/output/archive/`
- `scripts/tasting_notes/generate_flavor_profile_preview_from_uploaded_notes.py` -> `mv 'scripts/tasting_notes/generate_flavor_profile_preview_from_uploaded_notes.py' data/output/archive/`

## Review Required
- `frontend/lib/core/widgets/` -> Frontend logic requires manual review
- `frontend/lib/features/whisky/data/dto/` -> Frontend logic requires manual review
- `frontend/lib/features/whisky/data/repositories/db_whisky_repository_impl.dart` -> Frontend logic requires manual review
