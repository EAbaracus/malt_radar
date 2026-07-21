# ScotchGit Candidate Quality Gate

## Decision

- production import decision: **NO-GO**
- fail checks: blank_rating_signal: 214, non_reddit_url: 86
- production.db changed: NO
- production.db read mode: SQLite URI `mode=ro`

## Input Files

- `C:/Users/eltun/Documents/malt radar/data/output/scotchgit_review_candidates.csv` exists: YES
- `C:/Users/eltun/Documents/malt radar/output/import/production.db` exists: YES
- `C:/Users/eltun/Documents/malt radar/output/reports/189_scotchgit_real_candidate_report.md` exists: YES
- `C:/Users/eltun/Documents/malt radar/output/reports/190_scotchgit_match_quality_report.md` exists: YES

## Counts

- total rows: 11321
- unique product_name: 11321
- unique source_url: 10026
- duplicate source_url count: 1295
- source_url values with multiple product_name values: 771
- raw rating column blank rows: 11321
- usable rating signal blank rows: 214

## Match Confidence Distribution

- high_confidence_match: 1094
- needs_review: 1293
- unmatched: 8934

## Match Buckets

- High: 1094 (9.66%)
- Medium: 1293 (11.42%)
- Low: 8934 (78.92%)
- high confidence ratio: 9.66%

## Master DB Match Audit

- matched whisky_id values in CSV: 2387
- matched whisky_id values found in production.db: 2387
- matched whisky_id values missing from production.db: 0
- rows without matched_master_whisky_id: 8934

## Domain And Required Field Checks

- sample URL rows: 0
- blank product_name rows: 0
- blank source_url rows: 0
- blank reviewer rows: 0
- blank rating signal rows: 214
- non-Reddit source_url rows: 86

## Very Low Fuzzy Score Samples

- 100 Pipers | score=0 | status=unmatched | url=http://www.reddit.com/r/Scotch/comments/14uder/100_pipers_blend_review_10/c7ghjy2
- 1792 12 Year | score=0 | status=unmatched | url=https://www.reddit.com/r/bourbon/comments/dgybt5/review_151_1792_12_year/
- 1792 Full Proof Red Dog Wine & Spirits | score=0 | status=unmatched | url=https://www.reddit.com/r/bourbon/comments/7am8g5/review_94_1792_full_proof_store_pick_red_dog_wine/
- 1792 High Rye | score=0 | status=unmatched | url=https://www.reddit.com/r/bourbon/comments/6jw7mm/review_228_1792_high_rye/
- 4 Roses PS OESK | score=0 | status=unmatched | url=https://old.reddit.com/r/bourbon/comments/ahl3o8/whiskey_review_bourbon_42_network_48_four_roses/
- 4 Roses SiB OESK, 10yr 2mo, 121 proof | score=0 | status=unmatched | url=https://www.reddit.com/r/bourbon/comments/da1ud5/review_140_mystery_sample_series_sample_1/
- A.H. Hirsch 16 | score=0 | status=unmatched | url=https://www.reddit.com/r/bourbon/comments/2fe3gn/reviews_38_50_ah_hirsch_16_rittenhouse_25_bowman/
- A.H. Hirsch 16 gold foil | score=0 | status=unmatched | url=https://www.reddit.com/r/bourbon/comments/2i37pq/review_16_ah_hirsch_16_year_gold_foil/
- A.H. Hirsch 16 year Bourbon 1974 | score=0 | status=unmatched | url=https://www.reddit.com/r/bourbon/comments/cmktgb/review_100_ah_hirsch_16yr_bourbon_1974/
- Aberfeldy 16 1994 AD Rattray Cask #4017 | score=0 | status=unmatched | url=https://www.reddit.com/r/Scotch/comments/6fxxt0/review_156_aberfeldy_16yr_sc_1994_adrattray/
- Aberfeldy 18 1997 Cadenhead's | score=0 | status=unmatched | url=http://www.reddit.com/r/Scotch/comments/1uxc0p/balvenie_12_14_aberfeldy_18_and_mortlach_15/
- Aberfeldy 18 Distillery Hand Fill | score=0 | status=unmatched | url=https://www.reddit.com/r/Scotch/comments/9sku62/review_677_aberfeldy_18_distillery_hand_fill/
- Aberlour 10 (1990s bottling) | score=0 | status=unmatched | url=https://www.reddit.com/r/Scotch/comments/6boee8/aberlour_10_1990s_bottling_review/
- Aberlour 11 Duncan Taylor NC2 | score=0 | status=unmatched | url=http://www.reddit.com/r/Scotch/comments/pw83v/as_promised_a_review_of_duncan_taylors_nc2/c3sq5bp
- Aberlour 12 year old NCF | score=0 | status=unmatched | url=https://www.reddit.com/r/Scotch/comments/6zyjut/review_28_aberlour_12_year_old_ncf/
- Aberlour 13 Bourbon Distillery Exclusive | score=0 | status=unmatched | url=https://www.reddit.com/r/Scotch/comments/6fe7tt/scotland_stag_aberallow_me_to_introduce_myself/
- Aberlour 15 Cuvee Marie d'Ecosse | score=0 | status=unmatched | url=http://www.reddit.com/r/Scotch/comments/tfcsr/aberlour_15yo_horizontal_review_3x_15yo/
- Aberlour 16 Sherry Distillery Exclusive | score=0 | status=unmatched | url=https://www.reddit.com/r/Scotch/comments/6fe7tt/scotland_stag_aberallow_me_to_introduce_myself/
- Aberlour 17 Master of Malt | score=0 | status=unmatched | url=http://www.reddit.com/r/Scotch/comments/15gc6w/whiskymas_days_16_24/
- Aberlour 17 SMWS 54.35 | score=0 | status=unmatched | url=https://www.reddit.com/r/Scotch/comments/66xodd/review_14_smws_5435_aberlour_17/

## Top 20 High Review Count Products

- Ardbeg Uigeadail | reviews=178 | reviewer=_TiNe_ | score=100
- Highland Park 12 | reviews=176 | reviewer=bieliebielie | score=88
- Lagavulin 16 | reviews=173 | reviewer=Allumina | score=92
- Ardbeg 10 | reviews=170 | reviewer=lordhawkthefirst | score=90
- Laphroaig Quarter Cask | reviews=160 | reviewer=/r/scotch | score=100
- Talisker 10 | reviews=154 | reviewer=_wwsd | score=99
- Laphroaig 10 | reviews=147 | reviewer=12side | score=95
- Glenfiddich 12 | reviews=139 | reviewer=SPG2469 | score=96
- Glenmorangie 10 Original | reviews=127 | reviewer=Boyd86 | score=86
- Glenmorangie 12 Quinta Ruban | reviews=126 | reviewer=cake_my_day | score=97
- Balvenie 12 Doublewood | reviews=122 | reviewer=12side | score=96
- Bunnahabhain 12 | reviews=121 | reviewer=ahugenerd | score=94
- Glenlivet 12 | reviews=121 | reviewer=RudolphSchmidt | score=92
- Caol Ila 12 | reviews=115 | reviewer=_TiNe_ | score=92
- Balvenie 14 Caribbean Cask | reviews=102 | reviewer=12side | score=100
- Ardbeg Corryvreckan | reviews=98 | reviewer=12side | score=100
- Oban 14 | reviews=96 | reviewer=ahugenerd | score=88
- Old Weller Antique 107 | reviews=96 | reviewer=theslicknick6 | score=100
- Macallan 12 Sherry | reviews=95 | reviewer=_TiNe_ | score=86
- Johnnie Walker Black Label | reviews=93 | reviewer=lordhawkthefirst | score=91

## Shared Source URL Samples

- http://www.reddit.com/r/Scotch/comments/at771p/compass_box_13_reviews/ | products=13
- https://www.reddit.com/r/worldwhisky/comments/6l8v8m/reviews_106120_tws_great_canadian_whisky_tasting/ | products=13
- https://www.reddit.com/r/Scotch/comments/6me56u/arranpolcalypse_33_arrans_part_2_review/ | products=9
- https://www.reddit.com/r/Scotch/comments/5cla6n/review_3245_massen_whisky_fest_report/ | products=9
- https://www.reddit.com/r/bourbon/comments/7q90hn/1826_thirtysix_roses_oesf_obsf_obsv_oesq_loch_key/ | products=9
- https://www.reddit.com/r/worldwhisky/comments/7ktfzs/multireview_of_9_glenora_distillery_expressions/ | products=9
- http://www.reddit.com/r/Scotch/comments/32qefq/review_18_exclusive_malts_arran_12_cask_machir_bay/ | products=8
- http://www.reddit.com/r/Scotch/comments/ei97fa/game_of_thrones_malts_nine_reviews/ | products=8
- https://www.reddit.com/r/Scotch/comments/e9dkum/reviews_570578_a_flock_of_glendronach_single_cask/ | products=8
- https://www.reddit.com/r/Scotch/comments/6h7it3/scotland_stag_at_an_in_tomatin_last_day/ | products=8
- http://www.reddit.com/r/Scotch/comments/15gc6w/whiskymas_days_16_24/ | products=7
- http://www.reddit.com/r/Scotch/comments/27nf35/duncan_taylor_scotch_tasting_reviews_714/ | products=7
- https://www.reddit.com/r/Scotch/comments/2unc0w/reviews_5361_epic_malt_tasting_night/ | products=7
- https://www.reddit.com/r/Scotch/comments/du1xm5/reviews_453459_bunnahabhain_warehouse_9_tasting/ | products=7
- https://www.reddit.com/r/Scotch/comments/djskhv/cadenheads_warehouse_tasting_reviews_426432/ | products=7
- https://www.reddit.com/r/Scotch/comments/3s5bn7/review_314_spirits_in_the_sky_2015_favourites/ | products=7
- https://www.reddit.com/r/Scotch/comments/8vrwyz/glendronach_single_cask_multiple/ | products=7
- http://www.reddit.com/r/Scotch/comments/15lmto/christmas_haul_combined_megareview/ | products=6
- https://www.reddit.com/r/Scotch/comments/80r22n/reviews_17_scotch_malt_whisky_society_march_2018/ | products=6
- http://www.reddit.com/r/Scotch/comments/367nta/reviews_256264_balvenie_39_north_port_26_more/crbgazt | products=6

## Script Warnings

- None
