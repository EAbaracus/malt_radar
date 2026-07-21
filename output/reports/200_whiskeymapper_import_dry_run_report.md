# Whiskey Mapper Import Dry-Run Report

## Safety
- DB write: NO
- Run with `--apply` to insert rows.

## Inputs
- Preview CSV: `data\output\whiskeymapper_import_preview_remapped.csv`
- Production DB: `output\import\production.db`
- Backup path: `output\import\production_before_whiskeymapper_import.db`

## Counts
- Preview rows: 362
- import_candidate rows: 258
- flavor_profiles before count: 380
- skip_existing_profile rows: 84
- blocked rows: 20

## Preflight Checks
- FK missing among import candidates: 0
- Duplicate target whisky_id among import candidates: 0
- Existing flavor_profiles conflicts among import candidates: 258
- Missing component rows among import candidates: 0
- Backup parent directory ready: True

## Gate
- Decision: GO
