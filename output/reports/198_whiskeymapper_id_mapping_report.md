# Whiskey Mapper WDB to Production ID Mapping Report

## Safety
- Production DB write: NO
- `whiskies` write: NO
- `flavor_profiles` write: NO
- Outputs are mapping and dry-run preview CSVs only.

## Inputs
- Whiskey Mapper candidates: `data\output\whiskeymapper_final_import_candidates_high_only.csv`
- Production DB: `output\import\production.db`

## Existing DB Counts
- whiskies: 1831
- flavor_profiles: 122
- tasting_notes: 25
- staging_tasting_notes: 3

## Remap Status Counts
- remap_high_confidence: 342
- remap_needs_review: 1
- remap_unmatched: 1
- remap_duplicate: 18
- duplicate production whisky_id values: 8
- duplicate remap rows blocked: 18

## Import Preview Actions
- import_candidate: 258
- skip_existing_profile: 84
- block_needs_review: 1
- block_unmatched: 1
- block_duplicate_remap: 18
- block_missing_profile_components: 0

## Outputs
- Mapping CSV: `data\output\whiskeymapper_wdb_to_production_id_map.csv`
- Remapped preview CSV: `data\output\whiskeymapper_import_preview_remapped.csv`

## Gate
- Decision: GO
- Source rows: 362
- Import candidates: 258
- block_missing_fk: 0

## Duplicate Production IDs
- W000040: 2 Whiskey Mapper rows
- W000608: 2 Whiskey Mapper rows
- W000803: 2 Whiskey Mapper rows
- W000998: 2 Whiskey Mapper rows
- W001673: 2 Whiskey Mapper rows
- W001700: 12 Whiskey Mapper rows
- W001733: 2 Whiskey Mapper rows
- W001798: 2 Whiskey Mapper rows
