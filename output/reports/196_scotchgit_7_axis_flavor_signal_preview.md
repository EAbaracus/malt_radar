# ScotchGit 7-Axis Flavor Signal Preview

## Decision

- preview generation GO/NO-GO: **GO**
- production import status: **NO-GO**
- production.db changed: NO
- output rows are `candidate_preview_only`.

## Counts

- total preview whisky count: 986
- high_only count: 514
- high_plus_medium count: 230
- medium_only count: 242
- zero signal count: 396

## Axis Coverage Counts

- smoky: 227
- sweet: 209
- fruity: 313
- spicy: 2
- woody: 187
- maritime: 225
- sherry: 241

## Confidence Warnings

- region_only_low_confidence: 431
- zero_signal: 396
- medium_only_low_weight: 242
- keyword_signal_present: 159

## Coverage Warning

- spicy coverage is low (2); no synthetic spicy signal was generated.

## Top 20 Smoky

- White Oak Akashi 14 | id=W000140 | smoky=1.0 | strength=2.0 | high_only
- White Oak Akashi | id=W000849 | smoky=1.0 | strength=2.0 | medium_only
- White Oak Akashi NAS Blend | id=W001357 | smoky=1.0 | strength=2.0 | medium_only
- GlenDronach Peated Port Wood | id=W000996 | smoky=1.0 | strength=1.773 | high_only
- GlenDronach Peated | id=W001027 | smoky=1.0 | strength=1.25 | high_only
- Balvenie 16 Triple Cask | id=W000279 | smoky=1.0 | strength=1.2499 | high_plus_medium
- Cragganmore 12 Peated (Special Release 2019) | id=W000409 | smoky=1.0 | strength=1.2499 | high_plus_medium
- BenRiach 21 Authenticus Peated | id=W000955 | smoky=1.0 | strength=1.2499 | high_only
- Glenlivet Nadurra Peated Cask Finish | id=W000977 | smoky=1.0 | strength=1.2499 | high_plus_medium
- Balvenie 14 Peat Week | id=W001022 | smoky=1.0 | strength=1.2499 | high_plus_medium
- BenRiach Peated Quarter Cask | id=W001043 | smoky=1.0 | strength=1.2499 | high_only
- Benromach Peat Smoke | id=W001217 | smoky=1.0 | strength=1.2499 | high_plus_medium
- Tomintoul Peaty Tang | id=W001226 | smoky=1.0 | strength=1.2499 | high_only
- Glenrothes Peated Cask Reserve | id=W001080 | smoky=1.0 | strength=1.231 | high_only
- Longrow Peated | id=W001187 | smoky=1.0 | strength=1.195 | high_only
- Glen Moray Elgin Classic - Peated | id=W001066 | smoky=1.0 | strength=1.1617 | medium_only
- Caol Ila 12 Unpeated | id=W000445 | smoky=1.0 | strength=1.0833 | high_plus_medium
- Caol Ila 17 Unpeated 2015 | id=W000518 | smoky=1.0 | strength=1.0833 | high_only
- Caol Ila 15 Unpeated | id=W000740 | smoky=1.0 | strength=1.0833 | medium_only
- Bruichladdich Port Charlotte Scottish Barley | id=W001000 | smoky=1.0 | strength=1.0833 | medium_only

## Top 20 Sherry

- Kilkerran Work In Progress 6 Sherry Wood | id=W000525 | sherry=1.0 | strength=2.3077 | high_only
- Westland Sherry Wood | id=W000328 | sherry=1.0 | strength=2.0 | high_only
- Wemyss Velvet Fig | id=W000388 | sherry=1.0 | strength=2.0 | medium_only
- Penderyn Sherrywood | id=W000402 | sherry=1.0 | strength=2.0 | high_only
- Kavalan Sherry Oak | id=W000314 | sherry=1.0 | strength=1.8304 | high_plus_medium
- Macallan 12 Sherry | id=W000289 | sherry=1.0 | strength=1.5417 | medium_only
- Bruichladdich 21 Cuvee 407 PX | id=W000048 | sherry=1.0 | strength=1.25 | high_plus_medium
- Bunnahabhain 18 | id=W000079 | sherry=1.0 | strength=1.25 | high_plus_medium
- Kilchoman Red Wine Cask Matured | id=W000087 | sherry=1.0 | strength=1.25 | high_plus_medium
- Springbank 12 Cask Strength | id=W000120 | sherry=1.0 | strength=1.25 | high_plus_medium
- Kilchoman 2006 Single Cask | id=W000264 | sherry=1.0 | strength=1.25 | medium_only
- Bruichladdich Rocks | id=W000346 | sherry=1.0 | strength=1.25 | high_plus_medium
- Bruichladdich Sherry Classic | id=W000640 | sherry=1.0 | strength=1.25 | high_plus_medium
- Glenmorangie Sonnalta PX | id=W000182 | sherry=1.0 | strength=1.2306 | high_plus_medium
- Glen Garioch 15 Sherry Cask | id=W000283 | sherry=1.0 | strength=1.203 | high_plus_medium
- Aberlour A'bunadh batch #55 | id=W000047 | sherry=1.0 | strength=1.1969 | high_only
- Aberlour A'bunadh | id=W000001 | sherry=1.0 | strength=1.1904 | high_only
- Aberlour A'bunadh Batch #63 | id=W000037 | sherry=1.0 | strength=1.1904 | high_only
- Aberlour A'bunadh batch #37 | id=W000038 | sherry=1.0 | strength=1.1904 | high_only
- Aberlour A'bunadh batch #40 | id=W000042 | sherry=1.0 | strength=1.1904 | high_only

## Top 20 Maritime

- J.P. Wiser's 19 Seasoned Oak | id=W001460 | maritime=1.0 | strength=2.0 | medium_only
- Glenmorangie Milsean | id=W000330 | maritime=1.0 | strength=1.126 | high_only
- Buchanan's Red Seal | id=W001316 | maritime=1.0 | strength=1.0 | medium_only
- Alberta Premium Dark Horse | id=W001485 | maritime=1.0 | strength=1.0 | high_only
- Seagram's V.O. | id=W001591 | maritime=1.0 | strength=1.0 | high_plus_medium
- Kilkerran Work In Progress 6 Sherry Wood | id=W000525 | maritime=0.3077 | strength=2.3077 | high_only
- Kilkerran Work In Progress 4 | id=W000751 | maritime=0.25 | strength=0.4063 | high_only
- Springbank 16 Local Barley | id=W000925 | maritime=0.25 | strength=0.4062 | high_plus_medium
- Highland Park 12 | id=W000032 | maritime=0.25 | strength=0.3333 | high_plus_medium
- Highland Park 18 | id=W000061 | maritime=0.25 | strength=0.3333 | high_plus_medium
- Highland Park 21 | id=W000119 | maritime=0.25 | strength=0.3333 | high_plus_medium
- Highland Park 15 | id=W000214 | maritime=0.25 | strength=0.3333 | high_plus_medium
- Tobermory 15 | id=W000277 | maritime=0.25 | strength=0.3333 | high_plus_medium
- Tobermory 10 | id=W000635 | maritime=0.25 | strength=0.3333 | high_plus_medium
- Highland Park Harald | id=W000851 | maritime=0.25 | strength=0.3333 | high_plus_medium
- Talisker 57° North | id=W000954 | maritime=0.25 | strength=0.3333 | high_plus_medium
- Arran Machrie Moor Cask Strength | id=W001031 | maritime=0.25 | strength=0.3333 | high_plus_medium
- Highland Park 12 Viking Honor | id=W001072 | maritime=0.25 | strength=0.3333 | high_plus_medium
- Highland Park Einar | id=W001084 | maritime=0.25 | strength=0.3333 | high_plus_medium
- Jura Prophecy | id=W001213 | maritime=0.25 | strength=0.3333 | high_only

## Top 20 Fruity

- Wemyss Velvet Fig | id=W000388 | fruity=1.0 | strength=2.0 | medium_only
- Compass Box Orangerie | id=W001354 | fruity=1.0 | strength=1.0 | high_only
- Balvenie Tun 1401 Batch #3 | id=W000035 | fruity=0.25 | strength=0.6563 | medium_only
- Glen Grant 10 | id=W000017 | fruity=0.25 | strength=0.6562 | high_plus_medium
- Glenfarclas 15 | id=W000199 | fruity=0.25 | strength=0.6562 | high_plus_medium
- Mortlach 15 Gordon & MacPhail | id=W000228 | fruity=0.2416 | strength=0.6342 | high_plus_medium
- Glenrothes 1998 | id=W000263 | fruity=0.2324 | strength=0.61 | medium_only
- GlenDronach Cask Strength | id=W000739 | fruity=0.2096 | strength=0.6594 | high_plus_medium
- Aberlour 12 Non Chill Filtered | id=W000145 | fruity=0.208 | strength=0.546 | high_only
- Balvenie 12 Triple Cask | id=W000362 | fruity=0.208 | strength=0.546 | high_only
- Macallan Edition No. 2 | id=W000443 | fruity=0.208 | strength=0.546 | high_only
- Macallan Edition No. 4 | id=W000451 | fruity=0.208 | strength=0.546 | high_only
- Macallan Edition No. 3 | id=W000492 | fruity=0.208 | strength=0.546 | high_only
- Glenlivet Founder's Reserve | id=W000671 | fruity=0.208 | strength=0.546 | high_only
- Glenrothes Select Reserve | id=W000678 | fruity=0.208 | strength=0.546 | high_only
- AnCnoc 1975 | id=W000095 | fruity=0.2044 | strength=0.5366 | high_plus_medium
- Longmorn 15 | id=W000163 | fruity=0.2044 | strength=0.5366 | high_plus_medium
- GlenDronach 8 The Heilan | id=W000592 | fruity=0.2028 | strength=0.5013 | high_plus_medium
- Caol Ila Cask Strength | id=W000059 | fruity=0.201 | strength=0.7499 | high_plus_medium
- Balblair 1989 | id=W000257 | fruity=0.2 | strength=0.45 | high_only

## Duplicate Variant Examples

- W001621 | variants=24 | source_rows=24 | names=Willett Family Estate Bourbon; Willett Family Estate Bourbon 10 #200; Willett Family Estate Bourbon 10y; Willett Family Estate Bourbon 11 1030; Willett Family Estate Bourbon 11y; Willett Family Estate Bourbon 11y #438; Willett Family Estate Bourbon 12 #1672; Willett Family Estate Bourbon 12 #314
- W001384 | variants=21 | source_rows=21 | names=High West A MidWinter Nights Dram Act 2; High West A MidWinter Nights Dram Act 4; High West A Midwinter Nights Dram Act 1; High West A Midwinter Nights Dram Act 2.1; High West A Midwinter Nights Dram Act 2.2; High West A Midwinter Nights Dram Act 2.4; High West A Midwinter Nights Dram Act 2.5; High West A Midwinter Nights Dram Act 3
- W000120 | variants=19 | source_rows=19 | names=Springbank 12 Cask Strength; Springbank 12 Cask Strength - Batch 16; Springbank 12 Cask Strength 56.3%; Springbank 12 Cask Strength Batch 1; Springbank 12 Cask Strength Batch 10; Springbank 12 Cask Strength Batch 13; Springbank 12 Cask Strength Batch 14; Springbank 12 Cask Strength Batch 15
- W001662 | variants=16 | source_rows=16 | names=Elijah Craig Barrel Proof; Elijah Craig Barrel Proof Batch 10; Elijah Craig Barrel Proof Batch 12; Elijah Craig Barrel Proof Batch 2; Elijah Craig Barrel Proof Batch 7; Elijah Craig Barrel Proof Batch 8; Elijah Craig Barrel Proof Batch 9; Elijah Craig Barrel Proof Batch A117
- W001673 | variants=14 | source_rows=14 | names=Russel's Reserve Single Barrel K&L 246; Russell's Reserve SIngle Barrel Rye; Russell's Reserve Single Barrel Bourbon; Russell's Reserve Single Barrel Bourbon Binnys; Russell's Reserve Single Barrel Bourbon C+S; Russell's Reserve Single Barrel Bourbon JB's; Russell's Reserve Single Barrel Bourbon K&L; Russell's Reserve Single Barrel Bourbon NH
- W000346 | variants=12 | source_rows=12 | names=Bruichladdich 10; Bruichladdich 15; Bruichladdich 18; Bruichladdich 20; Bruichladdich 21; Bruichladdich 22; Bruichladdich Oloroso; Bruichladdich PC11
- W001477 | variants=11 | source_rows=11 | names=Wild Turkey 101; Wild Turkey 101 1994; Wild Turkey 101 1999; Wild Turkey 101 2004; Wild Turkey 101 2007; Wild Turkey 101 2009; Wild Turkey 101 2017; Wild Turkey 101 8
- W001722 | variants=11 | source_rows=11 | names=Evan Williams Single Barrel; Evan Williams Single Barrel 1997; Evan Williams Single Barrel 1998; Evan Williams Single Barrel 2000; Evan Williams Single Barrel 2001; Evan Williams Single Barrel 2003; Evan Williams Single Barrel 2004; Evan Williams Single Barrel 2005
- W000179 | variants=10 | source_rows=10 | names=Bruichladdich Port Charlotte 12; Bruichladdich Port Charlotte 17 2001 Maltbarn; Bruichladdich Port Charlotte 2001 Archives; Bruichladdich Port Charlotte 2002 SMWS 127.42; Bruichladdich Port Charlotte 2009 MC:01; Bruichladdich Port Charlotte MC:01; Bruichladdich Port Charlotte MC:01 2009; Bruichladdich Port Charlotte PC10
- W001142 | variants=10 | source_rows=10 | names=Laphroaig 10 Cask Strength Batch 004; Laphroaig 10 Cask Strength Batch 2; Laphroaig 10 Cask Strength Batch 4; Laphroaig 10 Cask Strength Batch 5; Laphroaig 10 Cask Strength Batch 6; Laphroaig 10 Cask Strength Batch 7; Laphroaig 10 Cask Strength Batch 8; Laphroaig 10 Cask Strength Batch 9
- W001398 | variants=10 | source_rows=10 | names=Willett Family Estate Rye; Willett Family Estate Rye 24y; Willett Family Estate Rye 25y; Willett Family Estate Rye 2y; Willett Family Estate Rye 3y; Willett Family Estate Rye 4y; Willett Family Estate Rye 5y; Willett Family Estate Rye 6y
- W001609 | variants=10 | source_rows=10 | names=William Larue Weller; William Larue Weller 2005; William Larue Weller 2006; William Larue Weller 2007; William Larue Weller 2010; William Larue Weller 2011; William Larue Weller 2013; William Larue Weller 2014
- W001618 | variants=9 | source_rows=9 | names=Four Roses Small Batch Limited Edition 2009; Four Roses Small Batch Limited Edition 2011; Four Roses Small Batch Limited Edition 2012; Four Roses Small Batch Limited Edition 2014; Four Roses Small Batch Limited Edition 2015; Four Roses Small Batch Limited Edition 2016; Four Roses Small Batch Limited Edition 2017; Four Roses Small Batch Limited Edition 2017 "Al Young"
- W000035 | variants=8 | source_rows=8 | names=Balvenie Tun 1401 Batch #2; Balvenie Tun 1401 Batch #3; Balvenie Tun 1401 Batch #4; Balvenie Tun 1401 Batch #5; Balvenie Tun 1401 Batch #6; Balvenie Tun 1401 Batch #8; Balvenie Tun 1401 Batch #9; Balvenie Tun 1401 Batch 9
- W001528 | variants=8 | source_rows=8 | names=Willett Family Estate Rye 11; Willett Family Estate Rye 25 #1778; Willett Family Estate Rye 4 #26A; Willett Family Estate Rye 4 Waxtop; Willett Family Estate Rye 4yr 110.2; Willett Family Estate Rye 8 #1406; Willett Family Estate Rye 8 Barrel 17; Willett Family Estate Rye XCF 1.0
- W001606 | variants=8 | source_rows=8 | names=George T. Stagg; George T. Stagg 2007; George T. Stagg 2011; George T. Stagg 2012; George T. Stagg 2013; George T. Stagg 2015; George T. Stagg 2017; George T. Stagg 2018
- W001644 | variants=8 | source_rows=8 | names=Old Rip Van Winkle 10; Old Rip Van Winkle 10 2013; Old Rip Van Winkle 10 2014; Old Rip Van Winkle 10 2015; Old Rip Van Winkle 10 2016; Old Rip Van Winkle 10 2018; Old Rip Van Winkle 2018; Old Rip Van Winkle 7 1977
- W001680 | variants=8 | source_rows=8 | names=Knob Creek 12 Single Barrel Reserve Binny's; Knob Creek 12 Single Barrel Reserve NASA Four Horsemen; Knob Creek 9 Single Barrel Reserve Binny's; Knob Creek Single Barrel Reserve; Knob Creek Single Barrel Reserve (Bourbon Hounds of Houston); Knob Creek Single Barrel Reserve NASA Rapture; Knob Creek Single Barrel Reserve: Binny's 2016; Knob Creek Single Barrel Reserve: NASA 2016
- W001769 | variants=8 | source_rows=8 | names=Jefferson's Ocean; Jefferson's Ocean 11; Jefferson's Ocean 2; Jefferson's Ocean 3; Jefferson's Ocean 5; Jefferson's Ocean 8; Jefferson's Ocean 9; Jefferson's Ocean CS 7
- W000263 | variants=7 | source_rows=7 | names=Glenrothes 11; Glenrothes 1985; Glenrothes 1987; Glenrothes 1988; Glenrothes 1991; Glenrothes 1994; Glenrothes 1998

## Output Files

- `C:/Users/eltun/Documents/malt radar/data/output/scotchgit_flavor_signal_preview.csv`
- `C:/Users/eltun/Documents/malt radar/output/reports/197_scotchgit_flavor_signal_samples.csv`
