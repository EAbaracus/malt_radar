# 177 — Flavor Gap Inventory

## Stats
* Total whiskies: 1831
* Whiskies with flavor profile: 122
* Whiskies missing flavor profile: 1709

## Missing by category
| Category | Count |
| --- | --- |
| Malt | 1119 |
| Blend | 289 |
| Bourbon | 192 |
| Rye | 80 |
| Grain | 6 |
| Wheat | 2 |
| Flavoured | 1 |
| Barley | 1 |

## Missing by distillery/brand top 20
| Distillery/Brand | Count |
| --- | --- |
| Box | 59 |
| Aberlour | 43 |
| Mackmyra | 33 |
| The Macallan | 29 |
| Amrut | 28 |
| Glenfiddich | 22 |
| Willett Distillery | 21 |
| Laphroaig | 20 |
| Bowmore | 20 |
| Kavalan | 19 |
| Forty Creek | 18 |
| Glengoyne | 18 |
| High West Distillery | 14 |
| The Glenlivet | 14 |
| The Balvenie | 13 |
| Glenmorangie | 13 |
| Wild Turkey Distillery | 12 |
| Talisker | 12 |
| Yamazaki | 10 |
| Glen Scotia | 9 |

## Missing by region
| Region | Count |
| --- | --- |
| Speyside | 84 |
| Highland | 72 |
| Islay | 48 |
| Islands | 12 |
| Campbeltown | 9 |
| Lowland | 7 |
| Harman | 1 |
| Blended Malt | 1 |

## Metadata
* Data sources inspected:
  - `frontend/assets/data/whisky_database_merged_max.csv`
  - `frontend/assets/data/flavor_profiles.csv`
  - `raw_sources/original_backend_data/production_data.csv`
  - `output/import/production.db` (whiskies table joined with flavor_profiles table)
* production.db changed: NO
* AppConfig.useDbApi=false: YES
