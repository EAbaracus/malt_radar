# Whiskey Mapper No-Match Rescue Report

## Safety
- Production DB write: NO
- Existing match CSV modified: NO
- This report only proposes rescue review candidates.

## Counts
- Input NO_MATCH rows: 58
- RESCUE_REVIEW: 32
- KEEP_NO_MATCH: 26

## Output
- `data\output\whiskeymapper_no_match_rescue_candidates.csv`

## RESCUE_REVIEW examples
- `Ardbeg Day` -> `Ardbeg An Oa` score=0.6667 overlap=0.5 reason=same_brand_family;token_overlap>=0.40_same_brand
- `Balblair 1990 2nd Release` -> `Balblair 1990 (all releases)` score=0.6965 overlap=0.6667 reason=same_brand_family;shared>=2_same_brand;token_overlap>=0.40_same_brand
- `Balcones Brimstone` -> `Balcones Distilling` score=0.603 overlap=0.3333 reason=same_brand_family
- `Balvenie 15 Single Barrel Sherry Cask` -> `Balvenie 15yo Single Barrel (Cask)` score=0.8132 overlap=1.0 reason=same_brand_family;shared>=2_same_brand;token_overlap>=0.40_same_brand
- `Balvenie 17 Madeira Cask` -> `Balvenie 14Y Caribbean Cask` score=0.6296 overlap=0.2 reason=same_brand_family
- `Balvenie 17 Peated Cask` -> `Balvenie 16yo Triple Cask` score=0.6161 overlap=0.2 reason=same_brand_family
- `Balvenie 21 Portwood` -> `Balvenie 21yo Port Wood` score=0.7951 overlap=1.0 reason=same_brand_family;shared>=2_same_brand;token_overlap>=0.40_same_brand;safe_term_same_brand:port wood
- `Balvenie Tun 1401 Batch #3` -> `Balvenie TUN 1401 (all batches)` score=0.7083 overlap=0.75 reason=same_brand_family;shared>=2_same_brand;token_overlap>=0.40_same_brand
- `BenRiach 16` -> `BenRiach 10yo` score=0.7642 overlap=0.3333 reason=same_brand_family
- `Bowmore Vault Edition 1st Release` -> `Bowmore Vault Edition First Release` score=0.8145 overlap=1.0 reason=same_brand_family;shared>=2_same_brand;token_overlap>=0.40_same_brand;safe_term_same_brand:vault edition
- `Bruichladdich Octomore 4.2_167 Comus` -> `Bruichladdich Octomore 6.2` score=0.7018 overlap=0.4286 reason=same_brand_family;shared>=2_same_brand;token_overlap>=0.40_same_brand
- `Bruichladdich Port Charlotte PC7 Sin an Doigh Ileach` -> `Bruichladdich Port Charlotte PC12 Oileanach Furachail` score=0.6017 overlap=0.2222 reason=same_brand_family;shared>=2_same_brand
- `Buchanan's 12 De Luxe` -> `Buchanan's 12yo Deluxe Blended` score=0.6681 overlap=0.75 reason=same_brand_family;shared>=2_same_brand;token_overlap>=0.40_same_brand;safe_term_same_brand:deluxe
- `Colonel E.H. Taylor Cured Oak` -> `Colonel E.H. Taylor Four Grain` score=0.6412 overlap=0.3333 reason=same_brand_family;shared>=2_same_brand
- `Glenmorangie Artein` -> `Glenmorangie Astar` score=0.6951 overlap=0.3333 reason=same_brand_family
- `Heaven Hill 6 Bottled in Bond` -> `Heaven Hill 6yo BiB` score=0.6864 overlap=1.0 reason=same_brand_family;shared>=2_same_brand;token_overlap>=0.40_same_brand;safe_term_same_brand:bib
- `Hibiki Japanese Harmony` -> `Hibiki Harmony` score=0.6728 overlap=0.6667 reason=same_brand_family;shared>=2_same_brand;token_overlap>=0.40_same_brand;safe_term_same_brand:harmony
- `High West A Midwinter Nights Dram` -> `High West Midwinter Night’s Dram Rye` score=0.7923 overlap=0.6667 reason=same_brand_family;shared>=2_same_brand;token_overlap>=0.40_same_brand;safe_term_same_brand:midwinter
- `Kilchoman Sherry Cask Release` -> `Kilchoman Sherry Single Cask` score=0.695 overlap=1.0 reason=same_brand_family;token_overlap>=0.40_same_brand
- `Laphroaig Triplewood` -> `Laphroaig Triple Wood` score=0.7639 overlap=1.0 reason=same_brand_family;shared>=2_same_brand;token_overlap>=0.40_same_brand;safe_term_same_brand:triple wood
- `Longrow Red 11 Fresh Port Cask` -> `Longrow Red 11yo Port Cask` score=0.8022 overlap=0.75 reason=same_brand_family;shared>=2_same_brand;token_overlap>=0.40_same_brand
- `Longrow Red 12 Fresh Pinot Noir Cask` -> `Longrow Red 12yo Pinot Noir Finish` score=0.7432 overlap=0.8333 reason=same_brand_family;shared>=2_same_brand;token_overlap>=0.40_same_brand
- `Macallan Classic Cut 2017` -> `Macallan Classic Cut (all editions)` score=0.637 overlap=0.5 reason=same_brand_family;token_overlap>=0.40_same_brand;safe_term_same_brand:classic cut
- `Oban Distiller's Edition` -> `Oban Distillers Edition (all vintages)` score=0.606 overlap=0.5 reason=same_brand_family;token_overlap>=0.40_same_brand
- `Old Grand Dad 100 Bottled in Bond` -> `Old Grand-Dad Bourbon 100 BiB` score=0.7036 overlap=1.0 reason=same_brand_family;shared>=2_same_brand;token_overlap>=0.40_same_brand;safe_term_same_brand:bib
- `Parker's Heritage Collection 6th: Blend of Mashbills` -> `Parker’s Heritage 6th Blend of Mashbills` score=0.8194 overlap=1.0 reason=same_brand_family;shared>=2_same_brand;token_overlap>=0.40_same_brand;safe_term_same_brand:heritage
- `Parker's Heritage Collection 7th: Promise of Hope` -> `Parker’s Heritage 7th 10yo Promise of Hope` score=0.75 overlap=0.8333 reason=same_brand_family;shared>=2_same_brand;token_overlap>=0.40_same_brand;safe_term_same_brand:heritage
- `Parker's Heritage Collection 8th: Wheat Whiskey` -> `Parker’s Heritage 8th 13yo Wheat Whiskey` score=0.7345 overlap=0.8 reason=same_brand_family;shared>=2_same_brand;token_overlap>=0.40_same_brand;safe_term_same_brand:heritage
- `Parker's Heritage Collection 9th: Malt Whiskey` -> `Parker’s Heritage 9th 8yo Malt Whiskey` score=0.7279 overlap=0.75 reason=same_brand_family;shared>=2_same_brand;token_overlap>=0.40_same_brand;safe_term_same_brand:heritage
- `Smooth Ambler Old Scout Bourbon 9` -> `Smooth Ambler Old Scout 7yo Bourbon` score=0.7964 overlap=0.6 reason=same_brand_family;shared>=2_same_brand;token_overlap>=0.40_same_brand;safe_term_same_brand:old scout
- `Smooth Ambler Old Scout Rye 8` -> `Smooth Ambler Old Scout 7yo Rye` score=0.8023 overlap=0.6 reason=same_brand_family;shared>=2_same_brand;token_overlap>=0.40_same_brand;safe_term_same_brand:old scout
- `Springbank 12 Burgundy` -> `Springbank 12yo Green` score=0.7041 overlap=0.5 reason=same_brand_family;shared>=2_same_brand;token_overlap>=0.40_same_brand

## KEEP_NO_MATCH examples
- `1792 Ridgemont Reserve` -> `Ellington Reserve 8yo` score=0.461 overlap=0.2 reason=weak_or_cross_brand
- `Ardbeg Airigh Nam Beist 1990` -> `Ardbeg Alligator` score=0.4545 overlap=0.1667 reason=same_brand_family
- `Ardmore 12 Port Wood Finish` -> `Glencadam 12yo Port Wood Finish` score=0.7139 overlap=0.3333 reason=weak_or_cross_brand
- `Baker's 107` -> `Baker’s 7yo Small Batch Bourbon` score=0.4468 overlap=0.25 reason=same_brand_family
- `Benrinnes 14 1999 Lady of the Glen` -> `Benrinnes 15yo F&F` score=0.4687 overlap=0.1667 reason=same_brand_family
- `Benrinnes 23` -> `Benrinnes 15yo F&F` score=0.5546 overlap=0.3333 reason=same_brand_family
- `Black Maple Hill` -> `Black Gate Distillery` score=0.541 overlap=0.2 reason=same_brand_family
- `Booker's 25th Anniversary` -> `Jack Daniel's 150th Anniversary` score=0.5495 overlap=0.1667 reason=weak_or_cross_brand
- `Dimple Pinch 15` -> `Glencadam 15yo` score=0.4407 overlap=0.25 reason=weak_or_cross_brand
- `Glenlivet 15 French Oak Reserve` -> `The Glenlivet 15Y French Oak` score=0.7973 overlap=0.8 reason=weak_or_cross_brand
- `Hazelburn 10` -> `Speyburn 10yo` score=0.5772 overlap=0.3333 reason=weak_or_cross_brand
- `John J. Bowman Single Barrel` -> `Jim Beam Single Barrel` score=0.5718 overlap=0.0 reason=weak_or_cross_brand
- `Johnny Drum Private Stock` -> `Glenmorangie Spios Private Edition No 9` score=0.3361 overlap=0.1429 reason=weak_or_cross_brand
- `Lagavulin Distillers Edition` -> `Dalwhinnie Distillers Edition` score=0.6453 overlap=0.0 reason=weak_or_cross_brand
- `Ledaig 7 /r/Scotch Community Cask` -> `Ledaig 13yo Amontillado Cask Finish` score=0.3872 overlap=0.2 reason=same_brand_family
- `Longrow Red 13 Malbec` -> `Longrow Red 11yo Port Cask` score=0.5435 overlap=0.4 reason=same_brand_family;shared>=2_same_brand;token_overlap>=0.40_same_brand
- `Michel Couvreur 12 Overaged Malt Whiskey` -> `Aberlour 12yo Double Cask Matured` score=0.3726 overlap=0.1429 reason=weak_or_cross_brand
- `Noah's Mill` -> `Towcester Mill Brewery Ltd` score=0.3356 overlap=0.2 reason=weak_or_cross_brand
- `Rebel Yell 10 Single Barrel` -> `Michter's 10yo Single Barrel Bourbon` score=0.5959 overlap=0.25 reason=weak_or_cross_brand
- `Rock Hill Farms Single Barrel Bourbon` -> `Jack Daniel's Single Barrel` score=0.5805 overlap=0.0 reason=weak_or_cross_brand
- `Rowan's Creek` -> `Ranger Creek` score=0.6272 overlap=0.3333 reason=weak_or_cross_brand
- `Smokehead` -> `Nikka Blended` score=0.2919 overlap=0.0 reason=weak_or_cross_brand
- `Springbank 17 Sherry Wood` -> `Westland Sherry Wood` score=0.5567 overlap=0.0 reason=weak_or_cross_brand
- `Talisker 175th Anniversary` -> `Jack Daniel's 150th Anniversary` score=0.5317 overlap=0.1667 reason=weak_or_cross_brand
- `Tamdhu 8 Signatory Cask Strength` -> `Amrut Cask Strength` score=0.5684 overlap=0.2 reason=weak_or_cross_brand
- `Very Old Barton Bottled In Bond` -> `Very Old Barton 6yo` score=0.586 overlap=0.6667 reason=same_brand_family;shared>=2_same_brand;token_overlap>=0.40_same_brand