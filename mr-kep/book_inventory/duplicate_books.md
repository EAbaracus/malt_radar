# Duplicate / Overlap Analysis

## Exact byte duplicates (same SHA256)

- SHA `056ab6524af7…`: ['Malt whisky yearbook 2019   the facts, the people, the news,', 'annas-arch-21eb2f4fc714']
- SHA `8fda7b30798f…`: ['Whisky Advocate - Wol  32 No  04 [Winter 2023] (TruePDF) pdf', 'OceanofPDF.com Whisky Advocate - Wol 32 No 04 Winter 2023 - Whisky Advocate']

## Same-title duplicates (different files/sources)

- `2023 libgen li`: ['[Scotch Whisky 2023-apr] - (2023) - libgen.li', '[Scotch Whisky The Whisky Magazine Annual Third Edition  2023] - (2023) - libgen.li']
- ``: ['[Scotch Whisky The Whisky Magazine Annual First Edition  2019]', 'annas-arch-21eb2f4fc714']

## Fuzzy / translation overlaps (manual review)

- **Whiskypedia (translation pair)**: ['Charles, MacLean   John, MacPherson - Whiskypedia  a compendium of Scottish whisky (2012, Skyhorse Publishing) - libgen.li', 'Маклин, Чарльз - Whiskypedia  An Introduction to Scotch Whisky (2012, Birlinn) - libgen.li']
- **Whisky Advocate 2020/2023 overlap**: ['50 - Whisky Advocate September 2020 pdf', 'Whisky Advocate December 2020 pdf', 'OceanofPDF.com Whisky Advocate - Wol 32 No 04 Winter 2023 - Whisky Advocate']

## Note
- Whiskypedia appears as EN (Skyhorse) + RU (Birlinn) editions — translation pair, keep both or dedupe to primary.
- Whisky Advocate 2020/2023 issues have naming clashes between OceanofPDF and TruePDF sources — verify same issue before dedup.