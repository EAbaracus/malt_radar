# Coverage Analysis — Sprint 05

> READ-ONLY. Compares genuine CSV sources against production.db (universe) and knowledge.db (already enriched).

## Reference state (read-only)

- **production.db universe:** 3,557 whiskies
- **knowledge.db enriched whisky_ids:** 1,544
- **knowledge.db citations (all sprints):** 10,138

## Genuine-source name coverage vs production.db

- **Distinct names in genuine sources:** 1160
- **Already present in production.db:** 495
- **MISSING from production.db (net-new candidate coverage):** 665

### Sample missing names (first 40 of 665)

- aberfeldy 12
- aberfeldy 16
- aberfeldy 18 french red wine casks from pauillac
- aberfeldy distillery
- aberlour 12
- aberlour 16 double cask
- achill island distillery
- adelphi
- ailsa bay
- akashi blended nas white oak
- akashi red
- akkeshi
- albyn
- allt-a-bhainne
- amrut distillery
- amrut indian cask strength
- amrut indian fusion single 50,0%
- ancnoc
- ancnoc 12
- ancnoc 18
- ancnoc peatheart 46%
- ancnoc sherry cask finish peated edition
- annandale distillery
- arbikie highland estate
- ardbeg 10
- ardbeg 8y for discussion
- ardbeg smoketrails cote rotie
- ardbeg spectacular
- ardbeg twenty something 23yo
- ardbeg wee beastie 5
- ardgowan
- ardlussa
- ardross
- argyll
- arran
- arran 10
- arran amarone cask finish
- arran port cask finish
- arran quarter cask whisky 'the bothy'
- arran sauternes cask finish

## Per-source field coverage (entity / metadata)

| Source | whisky_name | distillery | brand | region | ABV | age | flavor/tasting | rating |
|--------|:-----------:|:----------:|:-----:|:------:|:---:|:---:|:-------------:|:------:|
| `brands.csv` | ✓ | ✓ | ✓ | ✓ | — | — | — | — |
| `catalogue.csv` | ✓ | ✓ | ✓ | ✓ | — | ✓ | — | ✓ |
| `distilleries.csv` | ✓ | — | ✓ | ✓ | — | — | — | — |
| `htfw_world_whisky_brands.csv` | ✓ | — | ✓ | ✓ | — | — | — | — |
| `htfw_world_whisky_brands_enriched.csv` | ✓ | — | ✓ | ✓ | — | — | — | — |
| `manual_curated_tasting_notes_url_extract_draft.csv` | ✓ | — | — | — | — | ✓ | ✓ | ✓ |
| `whiskybase_export_sample.csv` | ✓ | ✓ | — | ✓ | ✓ | ✓ | — | ✓ |

## Already-enriched in knowledge.db (avoid re-ingest)

- The 1,544 whisky_ids already carrying consensus_nodes should be EXCLUDED from any future CSV ingestion.

## Conclusion

- Genuine CSV sources contain **665 net-new whisky/distillery names** absent from production.db — a real coverage opportunity.
- Flavor/tasting data is present ONLY in `manual_curated_tasting_notes_url_extract_draft.csv` (1 row, draft) — thin but unique.
- The remaining 541 CSVs are derived artifacts and contribute NO new source coverage.
