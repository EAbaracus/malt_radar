# P203C-FIX — 04 Parser Validation

Semantic parser success: **6/6** — every extracted `whisky_name` is a real whisky, not a section/category/site title.

## Extracted whisky names (fixture)

| source | whisky_name | semantic_ok |
|---|---|---|
| thewhiskyphiles | Glenmorangie 18 Year Old Signet Reserve | True |
| whiskymonster | Lagavulin 16 Year Old | True |
| thedramble | Clynelish 14 Year Old | True |
| whiskynotes_be | Ardbeg 10 Year Old | True |
| thewhiskeywash | Talisker 10 Year Old | True |
| wordsofwhisky | Highland Park 12 Year Old Viking Honour | True |

## Fields verified
whisky_name, distillery_raw (via crosswalk hint), abv, age, score, author, publication_date, url, source all extracted.
Semantic guard: a `whisky_name` equal to a known forbidden token (section/category/site) fails `test_parser_semantic_whisky_name`.
