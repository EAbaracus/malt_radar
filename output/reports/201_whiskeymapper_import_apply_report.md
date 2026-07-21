# Whiskey Mapper Import Apply Report

## Safety
- Backup created: `output\import\production_before_whiskeymapper_import.db`
- Transaction used: YES
- Rollback required: True

## Counts
- Preview rows: 362
- import_candidate rows before apply: 258
- flavor_profiles before count: 380
- insert_count: 0
- skip_existing_at_apply: 258
- flavor_profiles final count: 380
- expected final count: 380

## Post-Import Checks
- FK violations: 0
- Duplicate flavor_profiles whisky_id values: 0
- Error: insert_count is 0

## Gate
- Decision: NO-GO
