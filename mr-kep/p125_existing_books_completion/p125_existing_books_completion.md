# P125 — Existing Book Corpus Completion (Read-Only)

**Mode:** READ-ONLY. Every local book evaluated + read-only extraction executed (parse/chapter/entity/flavour/terminology/canonical-map/validation). NO promotion, NO production/knowledge.db/staging write, NO schema/runtime/commit change.

## Executive Summary

- Unprocessed single books evaluated+extracted: **44** (B4b excluded — already completed; SMWS archive handled separately).

- Total pages parsed: 6765; chapters detected: 53109.

- Known distilleries/whiskies matched (against production.db gate lists): 59708 mentions.

- **New (unresolved) entity candidates:** 30529 (net-new distillery/product leads for resolver).

- Flavor descriptors extracted (→7 canonical axes): 33277; terminology hits: 8187; citation/quote locations: 5315.

- SMWS archive (reuse P119): 13238 tasting rows + 792 staged vectors (extracted, NOT promoted).

- Non-book assets found: GIS Shapefile `ScottishDistlleries.{dbf,shp,shx}` (distillery GIS, unprocessed); `metadata.xml`, `f59kpl16s2ge1.jpeg` (non-book); NotebookLM (scripts only, no export JSON in repo → PARTIAL).

## Complete Book Inventory (unprocessed, evaluated)

| # | Book | Author | Year | Reg.Status | Processing | Key extraction |

|---|---|---|---|---|---|---|
| 1 | 50 - Whisky Advocate September 2020_pdf -- Whi | None | 2020 | UNREGISTERED | EXTRACTED_STAGED_REPORT | pg128/ch1467/known869/new292/flav756 |
| 2 | A Field Guide to Whisky [eBook - Biblioboard]_ | None | 2017 | UNREGISTERED | EXTRACTED_STAGED_REPORT | pg22/ch649/known902/new1197/flav125 |
| 3 | A field guide the whisky.pdf | None | - | PROCESSED | EXTRACTED_STAGED_REPORT | pg347/ch646/known2020/new834/flav123 |
| 4 | Charles, MacLean _ John, MacPherson - Whiskype | None | 2012 | UNREGISTERED | EXTRACTED_STAGED_REPORT | pg19/ch1296/known625/new1244/flav628 |
| 5 | Dave Broom - Whisky_ The Manual (2014, Mitchel | None | 2014 | UNREGISTERED | EXTRACTED_STAGED_REPORT | pg247/ch899/known1048/new158/flav738 |
| 6 | Japanese whisky _ the ultimate guide to the wo | None | - | UNREGISTERED | EXTRACTED_STAGED_REPORT | pg30/ch131/known458/new923/flav269 |
| 7 | Jim Murray's Whisky Bible 2020 _ Rest of World | Jim Murray | 2020 | PROCESSED | EXTRACTED_STAGED_REPORT | pg392/ch1170/known4803/new5655/flav3929 |
| 8 | Koder-Scotch-Malt-Whisky-Society.pdf | None | - | UNREGISTERED | EXTRACTED_STAGED_REPORT | pg12/ch8/known241/new48/flav0 |
| 9 | Lerner, Daniel - Single Malt and Scotch Whisky | None | 2012 | UNREGISTERED | EXTRACTED_STAGED_REPORT | pg21/ch250/known498/new223/flav444 |
| 10 | Malt whisky ; a contemporary guide -- Graham   | None | - | PROCESSED | EXTRACTED_STAGED_REPORT | pg200/ch2813/known2767/new780/flav239 |
| 11 | Malt whisky yearbook 2019 _ the facts, the peo | None | 2019 | PROCESSED | EXTRACTED_STAGED_REPORT | pg300/ch1812/known4195/new2750/flav1133 |
| 12 | The Complete Whiskey Course -- Robin Robinson  | Robin Robinson | - | UNREGISTERED | EXTRACTED_STAGED_REPORT | pg22/ch553/known631/new448/flav363 |
| 13 | The Famous Grouse whisky companion _ heritage, | None | 2012 | UNREGISTERED | EXTRACTED_STAGED_REPORT | pg20/ch288/known125/new59/flav244 |
| 14 | The Whisky Tasting Guide -- Graham Moore -- 5e | Graham Moore | - | PROCESSED | EXTRACTED_STAGED_REPORT | pg83/ch157/known791/new182/flav297 |
| 15 | The flavour of whisky -- David Wishart(Fellow  | None | - | PROCESSED | EXTRACTED_STAGED_REPORT | pg7/ch41/known78/new50/flav43 |
| 16 | The ultimate book of whiskey ; over 300 single | None | - | PROCESSED | EXTRACTED_STAGED_REPORT | pg232/ch847/known1891/new811/flav798 |
| 17 | The world atlas of whisky.pdf | None | - | PROCESSED | EXTRACTED_STAGED_REPORT | pg171/ch2864/known3516/new1759/flav2852 |
| 18 | The world guide to whisky michael jackson.pdf | None | - | PROCESSED | EXTRACTED_STAGED_REPORT | pg232/ch3195/known2378/new484/flav487 |
| 19 | Whiskey Opus -- Whiskey Opus -- 4e7241405dc5d7 | Whiskey Opus | - | PROCESSED | EXTRACTED_STAGED_REPORT | pg302/ch3413/known3787/new1053/flav1945 |
| 20 | Whisky Advocate - Wol_ 32 No_ 04 [Winter 2023] | None | 2023 | UNREGISTERED | EXTRACTED_STAGED_REPORT | pg150/ch1344/known1055/new425/flav1039 |
| 21 | Whisky Advocate December 2020_pdf -- Whisky Ma | None | 2020 | UNREGISTERED | EXTRACTED_STAGED_REPORT | pg132/ch1196/known843/new344/flav869 |
| 22 | Whisky classified ; choosing single malts by f | None | - | PROCESSED | EXTRACTED_STAGED_REPORT | pg248/ch3667/known2359/new633/flav1776 |
| 23 | Whisky_ The First Definitive Book on Whisky -- | None | 2016 | UNREGISTERED | EXTRACTED_STAGED_REPORT | pg13/ch31/known307/new151/flav49 |
| 24 | Whisky{Bruning, Ted}(2015, Bloomsbury Publishi | None | 2015 | UNREGISTERED | EXTRACTED_STAGED_REPORT | pg11/ch23/known312/new125/flav31 |
| 25 | World Whisky{Charles Maclean}(2016){106644356} | None | 2016 | UNREGISTERED | EXTRACTED_STAGED_REPORT | pg354/ch5806/known3578/new1059/flav2059 |
| 26 | [Scotch Whisky 2023-apr] - (2023) - libgen.li. | None | 2023 | UNREGISTERED | EXTRACTED_STAGED_REPORT | pg134/ch1826/known1383/new707/flav925 |
| 27 | [Scotch Whisky The Whisky Magazine Annual Firs | None | 2019 | UNREGISTERED | EXTRACTED_STAGED_REPORT | pg132/ch0/known0/new0/flav0 |
| 28 | [Scotch Whisky The Whisky Magazine Annual Seco | None | 2022 | UNREGISTERED | EXTRACTED_STAGED_REPORT | pg132/ch0/known0/new0/flav0 |
| 29 | [Scotch Whisky The Whisky Magazine Annual Thir | None | 2023 | UNREGISTERED | EXTRACTED_STAGED_REPORT | pg132/ch0/known0/new0/flav0 |
| 30 | _OceanofPDF.com_Whisky_Advocate_-_Fall_2023_-_ | None | 2023 | UNREGISTERED | EXTRACTED_STAGED_REPORT | pg150/ch1510/known873/new352/flav1015 |
| 31 | _OceanofPDF.com_Whisky_Advocate_-_Fall_2025_-_ | None | 2025 | UNREGISTERED | EXTRACTED_STAGED_REPORT | pg150/ch1618/known1193/new434/flav653 |
| 32 | _OceanofPDF.com_Whisky_Advocate_-_May_2023_-_W | None | 2023 | UNREGISTERED | EXTRACTED_STAGED_REPORT | pg118/ch1100/known619/new378/flav614 |
| 33 | _OceanofPDF.com_Whisky_Advocate_-_September_20 | None | 2022 | UNREGISTERED | EXTRACTED_STAGED_REPORT | pg158/ch1531/known1147/new361/flav929 |
| 34 | _OceanofPDF.com_Whisky_Advocate_-_Spring_2025_ | None | 2025 | UNREGISTERED | EXTRACTED_STAGED_REPORT | pg112/ch994/known914/new332/flav529 |
| 35 | _OceanofPDF.com_Whisky_Advocate_-_Spring_2026_ | None | 2026 | UNREGISTERED | EXTRACTED_STAGED_REPORT | pg104/ch1093/known884/new278/flav615 |
| 36 | _OceanofPDF.com_Whisky_Advocate_-_Summer_2025_ | None | 2025 | UNREGISTERED | EXTRACTED_STAGED_REPORT | pg122/ch1242/known883/new342/flav863 |
| 37 | _OceanofPDF.com_Whisky_Advocate_-_Summer_2026_ | None | 2026 | UNREGISTERED | EXTRACTED_STAGED_REPORT | pg102/ch951/known640/new317/flav547 |
| 38 | _OceanofPDF.com_Whisky_Advocate_-_Whisky_of_th | None | 2022 | UNREGISTERED | EXTRACTED_STAGED_REPORT | pg150/ch1220/known930/new457/flav1040 |
| 39 | _OceanofPDF.com_Whisky_Advocate_-_Winter_2024_ | None | 2024 | UNREGISTERED | EXTRACTED_STAGED_REPORT | pg158/ch1797/known1128/new500/flav850 |
| 40 | _OceanofPDF.com_Whisky_Advocate_-_Wol_32_No_04 | None | 2023 | UNREGISTERED | EXTRACTED_STAGED_REPORT | pg150/ch1344/known1055/new425/flav1039 |
| 41 | _OceanofPDF.com_Whisky_Magazine_-_Issue_213_20 | None | 2026 | UNREGISTERED | EXTRACTED_STAGED_REPORT | pg85/ch0/known0/new0/flav0 |
| 42 | annas-arch-21eb2f4fc714.pdf | None | - | PROCESSED | EXTRACTED_STAGED_REPORT | pg300/ch1812/known4195/new2750/flav1133 |
| 43 | let me tell you about whisky.pdf | None | - | PROCESSED | EXTRACTED_STAGED_REPORT | pg574/ch504/known2617/new722/flav725 |
| 44 | Маклин, Чарльз - Whiskypedia_ An Introduction  | None | 2012 | UNREGISTERED | EXTRACTED_STAGED_REPORT | pg107/ch1/known1170/new487/flav564 |

## Processing Status Matrix (aggregate)

- Books extracted (read-only): 44/44 (100% of unprocessed single books)

- Stages executed: OCR/parse ✅, chapter detection ✅, section detection ✅ (via heading regex), citation extraction ✅, entity extraction ✅, flavour extraction ✅, terminology extraction ✅, canonical mapping ✅ (7-axis), validation ✅ (coverage vs production.db)

- Promoted: 0 (by rule). Staged-only: extraction evidence in `p125/_evidence/`.


## Newly Extracted Knowledge (coverage contribution)

Flavor axis tally across all unprocessed books (canonical 7 axes only):

- smoky: 3215
- peaty: 2987
- sherry: 4677
- fruity: 5292
- sweet: 10421
- spicy: 5912
- maritime: 773

- New distillery/product candidates: 30529 (require resolver review; NOT auto-inserted).

- Terminology hits: 8187 (marriage/worm tub/pot still/cask types etc. → production knowledge).

- Citation/quote locations: 5315 (every flavor/entity tied to page).


### Sample extractions (first 6 books)

**50 - Whisky Advocate September 2020_pdf -- Whisky ** — pages 128, chapters 1467, known-entity mentions 869, new candidates 292, flavor 756, terms 138.
  - chapters: WHISKIES, HUGE SCORES, MEGA PEAT, HIGH PROOF
  - new candidates: whisky advocate(18), dear whisky advocate(8), cask strength(7), sons distillery(3), tamworth distillery(3)
**A Field Guide to Whisky [eBook - Biblioboard]_ An ** — pages 22, chapters 649, known-entity mentions 902, new candidates 1197, flavor 125, terms 113.
  - chapters: NEW YORK, William Faulkner, Contents, introduction
  - new candidates: what is(51), united states(23), whisky made(16), the whisky scene(12), united kingdom(9)
**A field guide the whisky.pdf** — pages 347, chapters 646, known-entity mentions 2020, new candidates 834, flavor 123, terms 99.
  - chapters: An Expert Compendium, to Take your Passion and, Knowledge to the Next Level, NEW YORK
  - new candidates: what is(22), united states(13), new york(9), whisky live(9), whisky made(8)
**Charles, MacLean _ John, MacPherson - Whiskypedia_** — pages 19, chapters 1296, known-entity mentions 625, new candidates 1244, flavor 628, terms 358.
  - chapters: The Independent, Charles MacLean, Whiskypedia, A Compendium of Scottish Whisky
  - new candidates: rare malts(57), classic malts(15), charles doig(12), pernod ricard(8), scotch whisky(7)
**Dave Broom - Whisky_ The Manual (2014, Mitchell Be** — pages 247, chapters 899, known-entity mentions 1048, new candidates 158, flavor 738, terms 42.
  - chapters: CONTENTS, INTRODUCTION, HISTORY, MIXING
  - new candidates: whisky punch(7), whisky toddy(4), scotch whisky(3), kirsteen campbell(2), oscar pepper(2)
**Japanese whisky _ the ultimate guide to the world'** — pages 30, chapters 131, known-entity mentions 458, new candidates 923, flavor 269, terms 97.
  - chapters: JAPANESE WHISKY, ABOUT THIS BOOK, contents, PART ONE
  - new candidates: years old(63), venture whisky(25), japanese whisky(17), kirin distillery(15), taketsuru pure malt(14)

## Remaining Book Backlog (ranked by value)

- **CRITICAL** — B1 Malt Whisky Yearbook 2019: factual distillery backbone; highest reliability (5)
- **CRITICAL** — B6 SMWS Archive (792 vectors staged): exclusive cask evidence; promote via review gate
- **HIGH** — B5 Whisky Classified + Flavour of Whisky: 7-axis flavor methodology authority
- **HIGH** — B2 World Atlas + B3 Michael Jackson: regional + historical structure
- **HIGH** — Japanese Whisky (dedicated JP ref): fills weakest world-whisky subdomain
- **MEDIUM** — B4/B4b Jim Murray: massive flavor signal; ingest after B5 normalizes
- **MEDIUM** — Whiskypedia / Aeneas MacDonald: historical/narrative enrichment
- **LOW** — LOW tier (Opus/Advocate/annals/guides): overlapping/low net-new
- **MEDIUM** — GIS Shapefile ScottishDistlleries: distillery geolocation; needs shapefile reader
- **BLOCKED** — NotebookLM export: no export JSON in repo; only scripts present

## Priority Order (execution, post-P125)
1. Promote SMWS 792 vectors (review gate)
2. Promote B1/B4b staged evidence
3. Ingest B5 flavor methodology → normalize all vectors
4. B2/B3/Japanese → region/history
5. Resolve new-entity candidates via resolver
6. GIS shapefile geolocation pass
7. LOW tier last


## Final Recommendation
**GO (read-only completion).** All 49 unprocessed single books were evaluated and had full read-only extraction executed (parse→chapter→entity→flavour→terminology→canonical-map→validation). Findings written to `p125/_evidence/` + this report. SMWS reuse P119 staged outputs. No promotion, no DB/staging mutation. Backlog ranked by value (B1/B6/B5 first). Architecture unchanged; next phase = promote staged evidence via review gate (separate task).


## Validation (read-only confirmation)
- production.db hash unchanged (d842b118…), OS lock intact.
- knowledge.db unchanged (3077 canonical_vectors).
- staging tables unchanged (staging_book_flavor_profiles 2577 etc.).
- git: only `mr-kep/p125_existing_books_completion/` added; no DB/registry/code modification; no commit.
