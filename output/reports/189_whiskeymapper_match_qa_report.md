# Whiskey Mapper Match QA Report

## Safety
- Production DB write: NO
- Match outputs only: YES

## Counts
- Total rows: 514
- HIGH: 362
- REVIEW: 94
- NO_MATCH: 58

## Outputs
- HIGH matches: `data\output\whiskeymapper_high_matches.csv`
- REVIEW matches: `data\output\whiskeymapper_review_matches.csv`
- NO_MATCH candidates: `data\output\whiskeymapper_no_match_candidates.csv`

## Lowest HIGH matches to manually spot-check
- `Glenlivet 25` -> `Glenlivet XXV 25yo` score=0.93 margin=0.1593 reason=name=0.857; token=0.667; distillery=0.720; margin=0.159
- `Dalmore 1263 King Alexander III` -> `Dalmore 12yo` score=0.94 margin=0.1035 reason=name=0.488; token=0.167; distillery=0.824; margin=0.103
- `Balvenie 15 Single Barrel` -> `Balvenie 15yo Single Barrel (Cask)` score=0.94 margin=0.1379 reason=name=0.909; token=1.000; distillery=0.421; margin=0.138
- `Aberlour 16` -> `Aberlour 16yo Double Cask Matured` score=0.94 margin=0.16 reason=name=0.524; token=0.500; distillery=0.410; margin=0.160
- `Lagavulin 12` -> `Lagavulin 12yo Cask Strength` score=0.94 margin=0.1693 reason=name=0.632; token=0.667; distillery=0.514; margin=0.169
- `Laphroaig 15` -> `Laphroaig 15yo (200th Anniversary)` score=0.94 margin=0.1693 reason=name=0.571; token=0.500; distillery=0.462; margin=0.169
- `Johnnie Walker Gold Label` -> `Johnnie Walker Gold Label Reserve` score=0.94 margin=0.177 reason=name=0.862; token=0.800; distillery=0.213; margin=0.177
- `Caol Ila 15 Unpeated` -> `Caol Ila 15yo Unpeated 2018` score=0.94 margin=0.2142 reason=name=0.889; token=0.800; distillery=0.485; margin=0.214
- `Macallan 12 Sherry` -> `Macallan 12yo Sherry Oak` score=0.94 margin=0.2297 reason=name=0.900; token=0.750; distillery=0.533; margin=0.230
- `Macallan 18 Sherry` -> `Macallan 18yo Sherry Oak` score=0.94 margin=0.2297 reason=name=0.900; token=0.750; distillery=0.533; margin=0.230
- `Macallan 25 Sherry` -> `Macallan 25yo Sherry Oak` score=0.94 margin=0.2297 reason=name=0.900; token=0.750; distillery=0.533; margin=0.230
- `Jim Beam Black 8 Double Aged` -> `Jim Beam` score=0.94 margin=0.2597 reason=name=0.444; token=0.333; distillery=1.000; margin=0.260
- `Russell's Reserve Single Barrel Rye` -> `Russell's Reserve Single Barrel` score=0.94 margin=0.2659 reason=name=0.939; token=0.750; distillery=0.238; margin=0.266
- `Wild Turkey Kentucky Spirit` -> `Wild Turkey Kentucky Spirit Single Barrel` score=0.94 margin=0.267 reason=name=0.794; token=0.800; distillery=0.667; margin=0.267
- `Bruichladdich Port Charlotte Scottish Barley` -> `Bruichladdich Port Charlotte Scottish Barley Heavily Peated` score=0.94 margin=0.2807 reason=name=0.854; token=0.714; distillery=0.361; margin=0.281
- `Angel's Envy Rye` -> `Angel’s Envy Rye (Rum-finished)` score=0.94 margin=0.2854 reason=name=0.744; token=0.750; distillery=0.615; margin=0.285
- `Balvenie 12 Single Barrel First Fill` -> `Balvenie 12yo Single Barrel` score=0.94 margin=0.2922 reason=name=0.820; token=0.600; distillery=0.485; margin=0.292
- `Buffalo Trace White Dog` -> `Buffalo Trace Bourbon` score=0.94 margin=0.2963 reason=name=0.722; token=0.500; distillery=1.000; margin=0.296
- `Colonel E.H. Taylor Small Batch` -> `Colonel E.H. Taylor Small Batch (BiB)` score=0.94 margin=0.3019 reason=name=0.938; token=0.800; distillery=0.213; margin=0.302
- `Henry McKenna 10 Single Barrel` -> `Henry McKenna 10yo Single Barrel BiB` score=0.94 margin=0.3103 reason=name=0.938; token=0.800; distillery=0.356; margin=0.310
- `Laphroaig 25 Cask Strength` -> `Laphroaig 25yo` score=0.94 margin=0.3141 reason=name=0.632; token=0.667; distillery=0.857; margin=0.314
- `Macallan Rare Cask` -> `Macallan Rare Cask (all batches)` score=0.94 margin=0.3171 reason=name=0.750; token=0.500; distillery=0.421; margin=0.317
- `Teeling Small Batch` -> `Teeling Small Batch (Rum Cask Finish)` score=0.94 margin=0.326 reason=name=0.704; token=0.750; distillery=0.467; margin=0.326
- `Talisker Distiller's Edition` -> `Talisker Distiller's Edition (all editions)` score=0.94 margin=0.3269 reason=name=0.812; token=0.600; distillery=0.327; margin=0.327
- `Glenmorangie Nectar D'Or 12` -> `Glenmorangie Nectar d'Or` score=0.94 margin=0.3307 reason=name=0.941; token=0.667; distillery=0.667; margin=0.331

## REVIEW queue examples
- `Bowmore 12` -> `Bowmore 12Y` score=1.0 margin=0.01 reason=name=1.000; token=1.000; distillery=1.000; margin=0.010
- `Deanston 12` -> `Deanston 12Y` score=1.0 margin=0.01 reason=name=1.000; token=1.000; distillery=1.000; margin=0.010
- `Glengoyne 12` -> `Glengoyne 12Y` score=1.0 margin=0.01 reason=name=1.000; token=1.000; distillery=1.000; margin=0.010
- `Redbreast 12` -> `Redbreast 12Y` score=1.0 margin=0.01 reason=name=1.000; token=1.000; distillery=1.000; margin=0.010
- `Talisker 10` -> `Talisker 10Y` score=1.0 margin=0.01 reason=name=1.000; token=1.000; distillery=1.000; margin=0.010
- `Stranahan's Colorado Whiskey` -> `Stranahan's Colorado Whiskey` score=0.99 margin=0.0 reason=name=1.000; token=1.000; distillery=0.564; margin=0.000
- `Amrut Spectrum 004` -> `Amrut Spectrum 004 (Batch 2)` score=0.94 margin=0.0 reason=name=0.818; token=0.600; distillery=1.000; margin=0.000
- `Angel's Envy Bourbon` -> `Angel's Envy Bourbon (Port-finished)` score=0.94 margin=0.0 reason=name=0.667; token=0.667; distillery=0.667; margin=0.000
- `Ardbeg Supernova` -> `Ardbeg Supernova 2019` score=0.94 margin=0.0 reason=name=0.865; token=0.667; distillery=0.444; margin=0.000
- `Barrell Bourbon` -> `Barrell Bourbon Batch 006` score=0.94 margin=0.0 reason=name=0.583; token=0.333; distillery=0.167; margin=0.000
- `Barrell Whiskey` -> `Barrell Whiskey Batch 001` score=0.94 margin=0.0 reason=name=0.750; token=0.333; distillery=0.125; margin=0.000
- `Basil Hayden's` -> `Basil Hayden’s 10yo Bourbon` score=0.94 margin=0.0 reason=name=0.903; token=0.667; distillery=0.240; margin=0.000
- `BenRiach 12 Sherry Matured` -> `BenRiach 12yo` score=0.94 margin=0.03 reason=name=0.595; token=0.500; distillery=0.842; margin=0.030
- `BenRiach 17 Solstice` -> `BenRiach 17yo Solstice Peated Port (both editions)` score=0.94 margin=0.0 reason=name=0.606; token=0.429; distillery=0.296; margin=0.000
- `Benromach 10 100 Proof` -> `Benromach 10yo` score=0.94 margin=0.03 reason=name=0.706; token=0.667; distillery=0.857; margin=0.030
- `Bernheim Original Small Batch Wheat Whiskey` -> `Bernheim` score=0.94 margin=0.01 reason=name=0.314; token=0.200; distillery=1.000; margin=0.010
- `Black Bottle` -> `Black Bottle (pre-2013)` score=0.94 margin=0.0 reason=name=0.727; token=0.500; distillery=0.286; margin=0.000
- `Booker's Bourbon` -> `Booker's Small Batch Straight Bourbon` score=0.94 margin=0.0 reason=name=0.432; token=0.250; distillery=0.216; margin=0.000
- `Bruichladdich Black Art` -> `Bruichladdich Black Art 1989` score=0.94 margin=0.0 reason=name=0.902; token=0.750; distillery=0.634; margin=0.000
- `Bruichladdich Islay Barley` -> `Bruichladdich Islay Barley (all vintages)` score=0.94 margin=0.03 reason=name=0.800; token=0.600; distillery=0.500; margin=0.030
- `Bruichladdich Port Charlotte 10` -> `Bruichladdich Port Charlotte 10yo Heavily Peated (Second Edition)` score=0.94 margin=0.0 reason=name=0.674; token=0.500; distillery=0.351; margin=0.000
- `Bushmills 10` -> `Bushmills 10yo Single Malt` score=0.94 margin=0.0 reason=name=0.667; token=1.000; distillery=1.000; margin=0.000
- `Compass Box 3 Year Old Deluxe` -> `Box` score=0.94 margin=0.03 reason=name=0.222; token=0.250; distillery=0.429; margin=0.030
- `Compass Box Flaming Heart` -> `Box` score=0.94 margin=0.0 reason=name=0.214; token=0.250; distillery=0.429; margin=0.000
- `Compass Box Peat Monster` -> `Compass Box Peat Monster 2014 - 10th Anniversary` score=0.94 margin=0.0 reason=name=0.686; token=0.571; distillery=0.133; margin=0.000

## NO_MATCH examples
- `Parker's Heritage Collection 6th: Blend of Mashbills` -> `Parker’s Heritage 6th Blend of Mashbills` score=0.8194 margin=0.2876 reason=name=0.879; token=0.833; distillery=0.392; margin=0.288
- `Bowmore Vault Edition 1st Release` -> `Bowmore Vault Edition First Release` score=0.8145 margin=0.0289 reason=name=0.941; token=0.667; distillery=0.333; margin=0.029
- `Balvenie 15 Single Barrel Sherry Cask` -> `Balvenie 15yo Single Barrel (Cask)` score=0.8132 margin=0.1577 reason=name=0.896; token=0.750; distillery=0.421; margin=0.158
- `Smooth Ambler Old Scout Rye 8` -> `Smooth Ambler Old Scout 7yo Rye` score=0.8023 margin=0.0768 reason=name=0.931; token=0.667; distillery=0.278; margin=0.077
- `Longrow Red 11 Fresh Port Cask` -> `Longrow Red 11yo Port Cask` score=0.8022 margin=0.2545 reason=name=0.889; token=0.800; distillery=0.235; margin=0.254
- `Glenlivet 15 French Oak Reserve` -> `The Glenlivet 15Y French Oak` score=0.7973 margin=0.2349 reason=name=0.793; token=0.800; distillery=0.818; margin=0.235
- `Smooth Ambler Old Scout Bourbon 9` -> `Smooth Ambler Old Scout 7yo Bourbon` score=0.7964 margin=0.013 reason=name=0.960; token=0.600; distillery=0.188; margin=0.013
- `Balvenie 21 Portwood` -> `Balvenie 21yo Port Wood` score=0.7951 margin=0.1909 reason=name=0.976; token=0.400; distillery=0.552; margin=0.191
- `High West A Midwinter Nights Dram` -> `High West Midwinter Night’s Dram Rye` score=0.7923 margin=0.2117 reason=name=0.899; token=0.571; distillery=0.621; margin=0.212
- `BenRiach 16` -> `BenRiach 10yo` score=0.7642 margin=0.0 reason=name=0.909; token=0.333; distillery=0.842; margin=0.000
- `Laphroaig Triplewood` -> `Laphroaig Triple Wood` score=0.7639 margin=0.1398 reason=name=0.976; token=0.250; distillery=0.600; margin=0.140
- `Parker's Heritage Collection 7th: Promise of Hope` -> `Parker’s Heritage 7th 10yo Promise of Hope` score=0.75 margin=0.2524 reason=name=0.841; token=0.714; distillery=0.235; margin=0.252
- `Longrow Red 12 Fresh Pinot Noir Cask` -> `Longrow Red 12yo Pinot Noir Finish` score=0.7432 margin=0.1756 reason=name=0.794; token=0.833; distillery=0.190; margin=0.176
- `Parker's Heritage Collection 8th: Wheat Whiskey` -> `Parker’s Heritage 8th 13yo Wheat Whiskey` score=0.7345 margin=0.1371 reason=name=0.833; token=0.667; distillery=0.245; margin=0.137
- `Parker's Heritage Collection 9th: Malt Whiskey` -> `Parker’s Heritage 9th 8yo Malt Whiskey` score=0.7279 margin=0.1418 reason=name=0.840; token=0.600; distillery=0.298; margin=0.142
- `Ardmore 12 Port Wood Finish` -> `Glencadam 12yo Port Wood Finish` score=0.7139 margin=0.1711 reason=name=0.821; token=0.600; distillery=0.278; margin=0.171
- `Balvenie Tun 1401 Batch #3` -> `Balvenie TUN 1401 (all batches)` score=0.7083 margin=0.0917 reason=name=0.852; token=0.429; distillery=0.432; margin=0.092
- `Springbank 12 Burgundy` -> `Springbank 12yo Green` score=0.7041 margin=0.099 reason=name=0.780; token=0.500; distillery=0.690; margin=0.099
- `Old Grand Dad 100 Bottled in Bond` -> `Old Grand-Dad Bourbon 100 BiB` score=0.7036 margin=0.1551 reason=name=0.778; token=0.500; distillery=0.703; margin=0.155
- `Bruichladdich Octomore 4.2_167 Comus` -> `Bruichladdich Octomore 6.2` score=0.7018 margin=0.0 reason=name=0.806; token=0.429; distillery=0.667; margin=0.000
- `Balblair 1990 2nd Release` -> `Balblair 1990 (all releases)` score=0.6965 margin=0.1554 reason=name=0.863; token=0.333; distillery=0.471; margin=0.155
- `Glenmorangie Artein` -> `Glenmorangie Astar` score=0.6951 margin=0.0167 reason=name=0.811; token=0.333; distillery=0.800; margin=0.017
- `Kilchoman Sherry Cask Release` -> `Kilchoman Sherry Single Cask` score=0.695 margin=0.0515 reason=name=0.737; token=0.667; distillery=0.486; margin=0.052
- `Heaven Hill 6 Bottled in Bond` -> `Heaven Hill 6yo BiB` score=0.6864 margin=0.0801 reason=name=0.739; token=0.500; distillery=0.786; margin=0.080
- `Hibiki Japanese Harmony` -> `Hibiki Harmony` score=0.6728 margin=0.2151 reason=name=0.757; token=0.667; distillery=0.133; margin=0.215