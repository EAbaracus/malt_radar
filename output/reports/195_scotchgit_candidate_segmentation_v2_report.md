# ScotchGit Candidate Segmentation V2 Report

## Decision

- production import GO/NO-GO: **NO-GO**
- production.db changed: NO
- low/unmatched rows are not production candidates.
- normalized source CSV was read only during segmentation.
- production import remains controlled by report/gate output only.

## Input

- input CSV: `C:/Users/eltun/Documents/malt radar/data/output/scotchgit_review_candidates_normalized.csv`

## Segment Counts

- total rows: 11321
- high rows: 911
- medium rows: 900
- quarantine rows: 9510
- high unique product_name: 911
- medium unique product_name: 900

## Risk Counts

- duplicate source_url conflict count: 771
- reddit dışı domain count: 86
- unmatched count: 8934
- source_url_verified=0 count: 86
- master_match_verified=1 count: 911

## Quarantine Reason Distribution

- master_match_verified_not_1: 9510
- missing_whiskyslist_metadata: 9479
- missing_matched_master_whisky_id: 8934
- match_status_unmatched: 8934
- quarantine: 8934
- match_score_below_75: 8172
- duplicate_source_url_conflict: 2066
- source_verified_not_1: 86
- non_reddit_domain: 86
- descriptor_product_name_prefix: 3

## Top 50 Quarantine Sample

- "Smoky" Islay 12 2019 Holyrood Distillery Cask | score=43 | status=unmatched | reasons=missing_matched_master_whisky_id|master_match_verified_not_1|match_status_unmatched|match_score_below_75|duplicate_source_url_conflict|descriptor_product_name_prefix|quarantine|missing_whiskyslist_metadata | url=https://www.reddit.com/r/Scotch/comments/dp8p0e/reviews_451452_holyrood_distillery_handfilled/
- "Sweet" Speyside 11 2007 Holyrood Distillery Cask | score=42 | status=unmatched | reasons=missing_matched_master_whisky_id|master_match_verified_not_1|match_status_unmatched|match_score_below_75|duplicate_source_url_conflict|descriptor_product_name_prefix|quarantine|missing_whiskyslist_metadata | url=https://www.reddit.com/r/Scotch/comments/dp8p0e/reviews_451452_holyrood_distillery_handfilled/
- 100 Pipers | score=0 | status=unmatched | reasons=missing_matched_master_whisky_id|master_match_verified_not_1|match_status_unmatched|match_score_below_75|quarantine|missing_whiskyslist_metadata | url=http://www.reddit.com/r/Scotch/comments/14uder/100_pipers_blend_review_10/c7ghjy2
- 1792 12 Year | score=0 | status=unmatched | reasons=missing_matched_master_whisky_id|master_match_verified_not_1|match_status_unmatched|match_score_below_75|quarantine|missing_whiskyslist_metadata | url=https://www.reddit.com/r/bourbon/comments/dgybt5/review_151_1792_12_year/
- 1792 225th Anniversary | score=69 | status=unmatched | reasons=missing_matched_master_whisky_id|master_match_verified_not_1|match_status_unmatched|match_score_below_75|quarantine|missing_whiskyslist_metadata | url=https://www.reddit.com/r/bourbon/comments/9ssqyk/review_35_1792_225th_anniversary/
- 1792 Bottled In Bond | score=49 | status=unmatched | reasons=missing_matched_master_whisky_id|master_match_verified_not_1|match_status_unmatched|match_score_below_75|quarantine|missing_whiskyslist_metadata | url=https://www.reddit.com/r/bourbon/comments/9ryi8f/review_34_1792_bottled_in_bond/
- 1792 Bottled In Bond Oak Liquor Cabinet Pick | score=51 | status=unmatched | reasons=missing_matched_master_whisky_id|master_match_verified_not_1|match_status_unmatched|match_score_below_75|duplicate_source_url_conflict|quarantine|missing_whiskyslist_metadata | url=https://www.reddit.com/r/bourbon/comments/a7jwdd/reviews_5153_oak_liquor_cabinet_1792_picks/
- 1792 Full Proof | score=67 | status=unmatched | reasons=missing_matched_master_whisky_id|master_match_verified_not_1|match_status_unmatched|match_score_below_75|quarantine|missing_whiskyslist_metadata | url=https://www.reddit.com/r/bourbon/comments/5aezxj/review_42_1792_full_proof/
- 1792 Full Proof Angel's Beverage | score=55 | status=unmatched | reasons=missing_matched_master_whisky_id|master_match_verified_not_1|match_status_unmatched|match_score_below_75|quarantine|missing_whiskyslist_metadata | url=https://www.reddit.com/r/bourbon/comments/863eqq/review_191_1792_full_proof_angels_beverage/?st=jf1arite&sh=5f5d31fc
- 1792 Full Proof Binny's | score=68 | status=unmatched | reasons=missing_matched_master_whisky_id|master_match_verified_not_1|match_status_unmatched|match_score_below_75|quarantine|missing_whiskyslist_metadata | url=https://www.reddit.com/r/bourbon/comments/6sm7k0/review_194_1792_full_proof_binnys_select/
- 1792 Full Proof Loch & K(e)y Microbatch | score=55 | status=unmatched | reasons=missing_matched_master_whisky_id|master_match_verified_not_1|match_status_unmatched|match_score_below_75|quarantine|missing_whiskyslist_metadata | url=https://www.reddit.com/r/bourbon/comments/7ajpxm/community_review_50_1792_full_proof/dpoxdh8/
- 1792 Full Proof Lueken's Store Pick | score=55 | status=unmatched | reasons=missing_matched_master_whisky_id|master_match_verified_not_1|match_status_unmatched|match_score_below_75|quarantine|missing_whiskyslist_metadata | url=https://www.reddit.com/r/bourbon/comments/7c4kfc/review_1_1792_full_proof_luekens_store_pick/
- 1792 Full Proof Oak Liquor Cabinet Pick | score=58 | status=unmatched | reasons=missing_matched_master_whisky_id|master_match_verified_not_1|match_status_unmatched|match_score_below_75|duplicate_source_url_conflict|quarantine|missing_whiskyslist_metadata | url=https://www.reddit.com/r/bourbon/comments/a7jwdd/reviews_5153_oak_liquor_cabinet_1792_picks/
- 1792 Full Proof Poison Girl | score=67 | status=unmatched | reasons=missing_matched_master_whisky_id|master_match_verified_not_1|match_status_unmatched|match_score_below_75|quarantine|missing_whiskyslist_metadata | url=https://www.reddit.com/r/bourbon/comments/67a74d/review_316_mystery_sample/
- 1792 Full Proof Red Dog Wine & Spirits | score=0 | status=unmatched | reasons=missing_matched_master_whisky_id|master_match_verified_not_1|match_status_unmatched|match_score_below_75|quarantine|missing_whiskyslist_metadata | url=https://www.reddit.com/r/bourbon/comments/7am8g5/review_94_1792_full_proof_store_pick_red_dog_wine/
- 1792 Full Proof Single Barrel Select - Midway Discount Liquors | score=41 | status=unmatched | reasons=missing_matched_master_whisky_id|master_match_verified_not_1|match_status_unmatched|match_score_below_75|quarantine|missing_whiskyslist_metadata | url=https://www.reddit.com/r/bourbon/comments/cbfl82/review_65_1792_full_proof_single_barrel_select/
- 1792 Full Proof store pick | score=64 | status=unmatched | reasons=missing_matched_master_whisky_id|master_match_verified_not_1|match_status_unmatched|match_score_below_75|quarantine|missing_whiskyslist_metadata | url=https://www.reddit.com/r/bourbon/comments/cmlpyf/review_101_1792_full_proof_store_pick_done_blind/
- 1792 Full Proof Yankee Spirits Select Barrel #2098 | score=42 | status=unmatched | reasons=missing_matched_master_whisky_id|master_match_verified_not_1|match_status_unmatched|match_score_below_75|quarantine|missing_whiskyslist_metadata | url=https://old.reddit.com/r/bourbon/comments/euzd9x/review_283_bourbon_1391792_full_proof_yankee/
- 1792 Full Proof – Midway Discount Liquors | score=54 | status=unmatched | reasons=missing_matched_master_whisky_id|master_match_verified_not_1|match_status_unmatched|match_score_below_75|quarantine|missing_whiskyslist_metadata | url=https://www.reddit.com/r/bourbon/comments/c9gpe3/review_113_1792_full_proof_midway_discount_liquors/
- 1792 High Rye | score=0 | status=unmatched | reasons=missing_matched_master_whisky_id|master_match_verified_not_1|match_status_unmatched|match_score_below_75|quarantine|missing_whiskyslist_metadata | url=https://www.reddit.com/r/bourbon/comments/6jw7mm/review_228_1792_high_rye/
- 1792 Port Finish | score=65 | status=unmatched | reasons=missing_matched_master_whisky_id|master_match_verified_not_1|match_status_unmatched|match_score_below_75|quarantine|missing_whiskyslist_metadata | url=https://www.reddit.com/r/bourbon/comments/6fbtzu/review_4_1792_port_finish/
- 1792 Ridgemont Reserve | score=56 | status=unmatched | reasons=missing_matched_master_whisky_id|master_match_verified_not_1|match_status_unmatched|match_score_below_75|quarantine|missing_whiskyslist_metadata | url=http://www.reddit.com/r/bourbon/comments/2i3for/review_28_1792_single_barrel_select_coxs_spirit/
- 1792 Single Barrel | score=74 | status=unmatched | reasons=missing_matched_master_whisky_id|master_match_verified_not_1|match_status_unmatched|match_score_below_75|quarantine|missing_whiskyslist_metadata | url=https://www.reddit.com/r/bourbon/comments/6zuga0/1792_ridgemont_reserve_single_barrel_review/
- 1792 Single Barrel (Crown Liquors, 7/12/16 Bottle) | score=51 | status=unmatched | reasons=missing_matched_master_whisky_id|master_match_verified_not_1|match_status_unmatched|match_score_below_75|quarantine|missing_whiskyslist_metadata | url=https://www.reddit.com/r/bourbon/comments/6ijts3/reviews_911_1792_threesome/
- 1792 Single Barrel Oak Liquor Cabinet Pick | score=61 | status=unmatched | reasons=missing_matched_master_whisky_id|master_match_verified_not_1|match_status_unmatched|match_score_below_75|duplicate_source_url_conflict|quarantine|missing_whiskyslist_metadata | url=https://www.reddit.com/r/bourbon/comments/a7jwdd/reviews_5153_oak_liquor_cabinet_1792_picks/
- 1792 Single Barrel Parkway Wine And Spirits | score=55 | status=unmatched | reasons=missing_matched_master_whisky_id|master_match_verified_not_1|match_status_unmatched|match_score_below_75|quarantine|missing_whiskyslist_metadata | url=https://www.reddit.com/r/bourbon/comments/5t92t4/review_283_mystery_sample/
- 1792 Small Batch | score=68 | status=unmatched | reasons=missing_matched_master_whisky_id|master_match_verified_not_1|match_status_unmatched|match_score_below_75|quarantine|missing_whiskyslist_metadata | url=http://www.reddit.com/r/bourbon/comments/3296zx/review_1792_small_batch/
- 1792 Sweet Wheat | score=68 | status=unmatched | reasons=missing_matched_master_whisky_id|master_match_verified_not_1|match_status_unmatched|match_score_below_75|quarantine|missing_whiskyslist_metadata | url=https://www.reddit.com/r/bourbon/comments/3inxll/review_5_1792_sweet_wheat/
- 1835 Bourbon Whiskey | score=43 | status=unmatched | reasons=missing_matched_master_whisky_id|master_match_verified_not_1|match_status_unmatched|match_score_below_75|quarantine|missing_whiskyslist_metadata | url=http://www.reddit.com/r/bourbon/comments/1a4fh8/first_review_1835_texas_bourbon/
- 291 Single Barrel Colorado Rye Whiskey | score=69 | status=unmatched | reasons=missing_matched_master_whisky_id|master_match_verified_not_1|match_status_unmatched|match_score_below_75|quarantine|missing_whiskyslist_metadata | url=https://www.reddit.com/r/bourbon/comments/9knwh7/review_23_291_single_barrel_colorado_rye_whiskey/
- 4 Roses PS OESK | score=0 | status=unmatched | reasons=missing_matched_master_whisky_id|master_match_verified_not_1|match_status_unmatched|match_score_below_75|quarantine|missing_whiskyslist_metadata | url=https://old.reddit.com/r/bourbon/comments/ahl3o8/whiskey_review_bourbon_42_network_48_four_roses/
- 4 Roses SiB OESK, 10yr 2mo, 121 proof | score=0 | status=unmatched | reasons=missing_matched_master_whisky_id|master_match_verified_not_1|match_status_unmatched|match_score_below_75|quarantine|missing_whiskyslist_metadata | url=https://www.reddit.com/r/bourbon/comments/da1ud5/review_140_mystery_sample_series_sample_1/
- 4Roses 130th Anniversary | score=71 | status=unmatched | reasons=missing_matched_master_whisky_id|master_match_verified_not_1|match_status_unmatched|match_score_below_75|quarantine|missing_whiskyslist_metadata | url=https://old.reddit.com/r/bourbon/comments/afv99z/whiskey_review_bourbon_40_network_44_4_roses/
- 601 Bourbon | score=73 | status=unmatched | reasons=missing_matched_master_whisky_id|master_match_verified_not_1|match_status_unmatched|match_score_below_75|quarantine|missing_whiskyslist_metadata | url=https://www.reddit.com/r/bourbon/comments/6wzndj/review_57_601_bourbon/?st=j6z55p2g&sh=87851b00
- 66 Gilead Crimson Rye | score=100 | status=review | reasons=master_match_verified_not_1|duplicate_source_url_conflict|missing_whiskyslist_metadata | url=https://www.reddit.com/r/worldwhisky/comments/4xeuyg/ww_reviews_2526_mystery_samples_from_u89justin/
- 66 Gilead Wild Oak | score=90 | status=review | reasons=master_match_verified_not_1|duplicate_source_url_conflict|missing_whiskyslist_metadata | url=https://www.reddit.com/r/worldwhisky/comments/4xeuyg/ww_reviews_2526_mystery_samples_from_u89justin/
- A Drop of the Irish Black Adder 2016 Sherry Cask Finish Single Cask | score=47 | status=unmatched | reasons=missing_matched_master_whisky_id|master_match_verified_not_1|match_status_unmatched|match_score_below_75|quarantine|missing_whiskyslist_metadata | url=https://old.reddit.com/r/worldwhisky/comments/aybrd0/a_drop_of_the_irish_blackadder_2016_sherry_finish/?
- A.D. Laws Four Grain Straight Bourbon | score=62 | status=unmatched | reasons=missing_matched_master_whisky_id|master_match_verified_not_1|match_status_unmatched|match_score_below_75|quarantine|missing_whiskyslist_metadata | url=https://www.reddit.com/r/bourbon/comments/3j08jt/review_7_ad_laws_four_grain_straight_bourbon_plus/
- A.D. Laws Four Grain Straight Bourbon BiB | score=59 | status=unmatched | reasons=missing_matched_master_whisky_id|master_match_verified_not_1|match_status_unmatched|match_score_below_75|quarantine|missing_whiskyslist_metadata | url=https://www.reddit.com/r/bourbon/comments/6mmppa/review_365_mystery_sample/
- A.D. Laws Secale Straight Rye | score=65 | status=unmatched | reasons=missing_matched_master_whisky_id|master_match_verified_not_1|match_status_unmatched|match_score_below_75|quarantine|missing_whiskyslist_metadata | url=https://www.reddit.com/r/bourbon/comments/7ucpdg/review_107_ad_laws_secale_straight_rye/
- A.H. Hirsch 16 | score=0 | status=unmatched | reasons=missing_matched_master_whisky_id|master_match_verified_not_1|match_status_unmatched|match_score_below_75|duplicate_source_url_conflict|quarantine|missing_whiskyslist_metadata | url=https://www.reddit.com/r/bourbon/comments/2fe3gn/reviews_38_50_ah_hirsch_16_rittenhouse_25_bowman/
- A.H. Hirsch 16 gold foil | score=0 | status=unmatched | reasons=missing_matched_master_whisky_id|master_match_verified_not_1|match_status_unmatched|match_score_below_75|quarantine|missing_whiskyslist_metadata | url=https://www.reddit.com/r/bourbon/comments/2i37pq/review_16_ah_hirsch_16_year_gold_foil/
- A.H. Hirsch 16 year Bourbon 1974 | score=0 | status=unmatched | reasons=missing_matched_master_whisky_id|master_match_verified_not_1|match_status_unmatched|match_score_below_75|quarantine|missing_whiskyslist_metadata | url=https://www.reddit.com/r/bourbon/comments/cmktgb/review_100_ah_hirsch_16yr_bourbon_1974/
- Aberfeldy 12 | score=92 | status=review | reasons=master_match_verified_not_1|duplicate_source_url_conflict|missing_whiskyslist_metadata | url=http://www.reddit.com/r/Scotch/comments/15lmto/christmas_haul_combined_megareview/
- Aberfeldy 12 Year Old | score=80 | status=review | reasons=master_match_verified_not_1|duplicate_source_url_conflict|missing_whiskyslist_metadata | url=https://www.reddit.com/r/Scotch/comments/ajx851/awkwardly_late_whisky_advent_calendar_omnibus/
- Aberfeldy 16 "Ramble" Single Cask | score=57 | status=unmatched | reasons=missing_matched_master_whisky_id|master_match_verified_not_1|match_status_unmatched|match_score_below_75|quarantine|missing_whiskyslist_metadata | url=https://www.reddit.com/r/Scotch/comments/9fnuml/review_aberfeldy_bramble_16y/
- Aberfeldy 16 1994 AD Rattray Cask #4017 | score=0 | status=unmatched | reasons=missing_matched_master_whisky_id|master_match_verified_not_1|match_status_unmatched|match_score_below_75|quarantine|missing_whiskyslist_metadata | url=https://www.reddit.com/r/Scotch/comments/6fxxt0/review_156_aberfeldy_16yr_sc_1994_adrattray/
- Aberfeldy 18 1997 Cadenhead's | score=0 | status=unmatched | reasons=missing_matched_master_whisky_id|master_match_verified_not_1|match_status_unmatched|match_score_below_75|quarantine|missing_whiskyslist_metadata | url=http://www.reddit.com/r/Scotch/comments/1uxc0p/balvenie_12_14_aberfeldy_18_and_mortlach_15/
- Aberfeldy 18 Distillery Hand Fill | score=0 | status=unmatched | reasons=missing_matched_master_whisky_id|master_match_verified_not_1|match_status_unmatched|match_score_below_75|quarantine|missing_whiskyslist_metadata | url=https://www.reddit.com/r/Scotch/comments/9sku62/review_677_aberfeldy_18_distillery_hand_fill/
- Aberfeldy 18 Single Cask Hand Filled 1998 | score=51 | status=unmatched | reasons=missing_matched_master_whisky_id|master_match_verified_not_1|match_status_unmatched|match_score_below_75|quarantine|missing_whiskyslist_metadata | url=https://www.reddit.com/r/Scotch/comments/8qws0p/review_201_aberfeldy_single_cask_hand_filled/

## Output Files

- `C:/Users/eltun/Documents/malt radar/data/output/scotchgit_candidates_high_confidence.csv`
- `C:/Users/eltun/Documents/malt radar/data/output/scotchgit_candidates_medium_confidence.csv`
- `C:/Users/eltun/Documents/malt radar/data/output/scotchgit_candidates_quarantine.csv`
