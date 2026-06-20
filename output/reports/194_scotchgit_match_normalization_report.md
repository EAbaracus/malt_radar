# ScotchGit Match Status Normalization Report

## Scope

- Existing candidate CSV remains backward compatible; `source_verified` is retained.
- New fields separate source URL verification from master whisky match verification.
- production.db was opened read-only with SQLite URI `mode=ro`.

## Counts

- total rows: 11321
- source_url_verified=1: 11235
- source_url_verified=0: 86
- master_match_verified=1: 911
- master_match_verified=0: 10410
- duplicate source_url conflict URLs: 771
- production.db changed: NO

## Normalized Match Status

- matched: 911
- review: 1476
- unmatched: 8934

## Normalized Import Recommendation

- candidate_only_high_confidence: 911
- manual_review: 1476
- quarantine: 8934

## Quarantine Reason Distribution

- legacy_review_before_import: 11321
- missing_whiskyslist_metadata: 11245
- missing_matched_master_whisky_id: 8934
- match_status_unmatched: 8934
- match_score_below_75: 8172
- duplicate_source_url_conflict: 2066
- source_url_not_reddit: 86

## Output

- normalized CSV: `C:/Users/eltun/Documents/malt radar/data/output/scotchgit_review_candidates_normalized.csv`

## Script Warnings

- Skipped 'Aberfeldy 1994 Wemyss' because no real Reddit review URL was found.
- Skipped 'Ben Nevis 17 Alambic Classique' because no real Reddit review URL was found.
- Skipped 'Ben Nevis 1991 Signatory' because no real Reddit review URL was found.
- Skipped 'BenRiach 1994 cask #806' because no real Reddit review URL was found.
- Skipped 'Benrinnes 34 1976 G&M' because no real Reddit review URL was found.
- Skipped 'Bruichladdich micro provenance cask exploration series Château Latour 1992' because no real Reddit review URL was found.
- Skipped 'Bruichladdich Port Charlotte 10 Second Limited Edition' because no real Reddit review URL was found.
- Skipped 'Bunnahabhain 1991 Wemyss' because no real Reddit review URL was found.
- Skipped 'Chivas Regal Mizunara' because no real Reddit review URL was found.
- Skipped 'Chivas Regal XV' because no real Reddit review URL was found.
- Skipped 'Clynelish 1995 Signatory' because no real Reddit review URL was found.
- Skipped 'Croftengea 10y SCN' because no real Reddit review URL was found.
- Skipped 'Dalwhinnie 25 1989' because no real Reddit review URL was found.
- Skipped 'Edradour 2004 Signatory' because no real Reddit review URL was found.
- Skipped 'Glen Scotia 1991 Wemyss' because no real Reddit review URL was found.
- Skipped 'Glenglassaugh 1978' because no real Reddit review URL was found.
- Skipped 'John Walker & Sons Private Collection 2015' because no real Reddit review URL was found.
- Skipped 'John Walker & Sons Private Collection 2016' because no real Reddit review URL was found.
- Skipped 'John Walker & Sons Private Collection 2017' because no real Reddit review URL was found.
- Skipped 'Johnnie Walker 15 Green Label' because no real Reddit review URL was found.
- Skipped 'Johnnie Walker Blenders' Batch Red Rye Finish' because no real Reddit review URL was found.
- Skipped 'Johnnie Walker Blenders' Batch Rum Cask Finish' because no real Reddit review URL was found.
- Skipped 'Johnnie Walker Blue Label Brora and Rare' because no real Reddit review URL was found.
- Skipped 'Johnnie Walker Blue Label Port Ellen and Rare' because no real Reddit review URL was found.
- Skipped 'Johnnie Walker Red Label Export Blend' because no real Reddit review URL was found.
- Skipped 'Kinclaith 40 1969 Signatory Vintage' because no real Reddit review URL was found.
- Skipped 'Knockando 25' because no real Reddit review URL was found.
- Skipped 'Longmorn 22 TheWhiskyCask' because no real Reddit review URL was found.
- Skipped 'McIntyre Blended Scotch' because no real Reddit review URL was found.
- Skipped 'Original Jesse James' because no real Reddit review URL was found.
- Skipped 'Ransom Whippersnapper' because no real Reddit review URL was found.
- Skipped 'Reunion Dram 25 W&D' because no real Reddit review URL was found.
- Skipped 'Tobermory 1972' because no real Reddit review URL was found.
- Skipped 'Virginia Highland Malt Whisky (Loch & K(e)y)' because no real Reddit review URL was found.
- Skipped 'Whisky Name' because no real Reddit review URL was found.
