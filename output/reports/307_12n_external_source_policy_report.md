# External Whisky Dataset Source Registry & Safe Import Policy (AŞAMA 12N)

## Audit Dependencies
- Missing 12K/12M Reports: 0


## Policy Overview
- **Direct Import Allowed**: 0
- **Staging Allowed**: 10
- **Full Text Blocked**: 9
- **License Review Required**: 9

## Sources Registered
Total classified: 10

### Full Text Blocked Sources (Copyright Risk)
- **Whisky Advocate / Kaggle scotch reviews**: Description contains copyrighted tasting notes.
- **koki25ando/Whisky-Data-Scraping GitHub repo**: Fragile scraping script. Same data as SRC_001.
- **whisky.com distilleries**: Factual metadata.
- **iDrinkScotch distillery data**: Factual metadata.
- **iDrinkScotch independent bottlers**: Factual metadata.
- **Whiskey Mapper**: API terms must be reviewed.
- **Master of Malt pages**: Tasting notes are copyrighted. Scrape strictly limited to factual metadata (ABV, price).
- **The Whisky Exchange pages**: Tasting notes are copyrighted. Factual data only.
- **Whiskybase**: Strong ToS restrictions likely. Need explicit permission.

## DB Integrity
- `production.db` SHA256 Hash: E8F1839E312FE474A43F3F224D5C7D57E213F28DB75545516D242788FDCF36A8

## Gate Status
- **Status**: GO_POLICY_ONLY
