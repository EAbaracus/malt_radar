# Whiskey Mapper Malt Radar Match Dry Run Report

## Safety
- Production DB write: NO
- Raw Whiskey Mapper data modified: NO
- Malt Radar master modified: NO

## Inputs
- Whiskey Mapper joined candidates: `data\output\whiskeymapper_joined_candidates.csv`
- Malt Radar master CSV: `backend\data\whisky_database_merged_max.csv`

## Counts
- Whiskey Mapper rows: 514
- Malt Radar master rows indexed: 2986
- Output match rows: 514

## Decisions
- HIGH: 362
- REVIEW: 94
- NO_MATCH: 58

## Output
- `data\output\whiskeymapper_malt_radar_match_candidates.csv`

## Decision rules
- HIGH: score >= 0.92 and margin >= 0.03
- REVIEW: score >= 0.84
- NO_MATCH: below review threshold

## Top HIGH examples
- `1792 Full Proof` -> `Barton 1792 Full Proof Bourbon` score=0.94
- `1792 Port Finish` -> `Barton 1792 Port Finished Bourbon` score=0.94
- `1792 Small Batch` -> `Barton 1792 Small Batch Bourbon` score=0.94
- `1792 Sweet Wheat` -> `Barton 1792 Sweet Wheat Bourbon` score=0.94
- `Aberfeldy 12` -> `Aberfeldy 12yo` score=0.99
- `Aberfeldy 21` -> `Aberfeldy 21yo` score=0.99
- `Aberlour 10` -> `Aberlour 10yo` score=0.99
- `Aberlour 12 Double Cask Matured` -> `Aberlour 12yo Double Cask Matured` score=0.99
- `Aberlour 12 Non Chill Filtered` -> `Aberlour 12yo Non-Chill-Filtered` score=0.99
- `Aberlour 16` -> `Aberlour 16yo Double Cask Matured` score=0.94

## Top REVIEW examples
- `Amrut Spectrum 004` -> `Amrut Spectrum 004 (Batch 2)` score=0.94
- `Angel's Envy Bourbon` -> `Angel's Envy Bourbon (Port-finished)` score=0.94
- `Ardbeg Supernova` -> `Ardbeg Supernova 2019` score=0.94
- `Arran 10` -> `Arran Malt 10yo` score=0.91
- `Arran 12 Cask Strength` -> `Arran Malt 12yo Cask Strength (all editions)` score=0.91
- `Arran 14` -> `Arran Malt 14yo` score=0.91
- `Arran Amarone Cask Finish` -> `Arran Malt Amarone Cask Finish` score=0.91
- `Arran Machrie Moor` -> `Arran Malt Machrie Moor Cask Strength` score=0.91
- `Arran Port Cask Finish` -> `Arran Malt Port Cask Finish` score=0.91
- `Arran Sauternes Cask Finish` -> `Arran Malt Sauternes Finish` score=0.91

## NO_MATCH examples
- `1792 Ridgemont Reserve` -> `Ellington Reserve 8yo` score=0.461
- `Ardbeg Airigh Nam Beist 1990` -> `Ardbeg Alligator` score=0.4545
- `Ardbeg Day` -> `Ardbeg An Oa` score=0.6667
- `Ardmore 12 Port Wood Finish` -> `Glencadam 12yo Port Wood Finish` score=0.7139
- `Baker's 107` -> `Baker’s 7yo Small Batch Bourbon` score=0.4468
- `Balblair 1990 2nd Release` -> `Balblair 1990 (all releases)` score=0.6965
- `Balcones Brimstone` -> `Balcones Distilling` score=0.603
- `Balvenie 15 Single Barrel Sherry Cask` -> `Balvenie 15yo Single Barrel (Cask)` score=0.8132
- `Balvenie 17 Madeira Cask` -> `Balvenie 14Y Caribbean Cask` score=0.6296
- `Balvenie 17 Peated Cask` -> `Balvenie 16yo Triple Cask` score=0.6161