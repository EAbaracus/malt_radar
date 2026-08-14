# P203C — 03 Parser Report

Parsed without exception: **15/15** (no crashes).
**Semantic parser success: 0/15** — every captured `whisky_raw_name` is a site-section title, not a review's whisky.

## Sample extracted raw_names (evidence of wrong-page extraction)

| source | whisky_raw_name | distillery_hint |
|---|---|---|
| thedramble | Tastings | tastings |
| thedramble | Bottle Name:A Good Old Fashioned Christmas Whisky  | bottle |
| thedramble | Undisclosed Speyside | speyside |
| thedramble | Bottle Name:A Good Old Fashioned Christmas Whisky  | bottle |
| thedramble | Bottle Name:Black Friday 2023 Edition | bottle |
| whiskynotes_be | WhiskyNotes | whiskynotes |
| whiskynotes_be | WhiskyNotes | whiskynotes |
| whiskynotes_be | WhiskyNotes | whiskynotes |
| whiskynotes_be | WhiskyNotes | whiskynotes |
| whiskynotes_be | WhiskyNotes | whiskynotes |
| thewhiskeywash | Whiskey Reviews | whiskey |
| thewhiskeywash | American WhiskeyReviews | american |
| thewhiskeywash | Scotch WhiskyReviews | scotch |
| thewhiskeywash | World WhiskeyReviews | world |
| thewhiskeywash | Bourbon Reviews | bourbon |

## Finding
- `parse_article` correctly reads `<h1>`, but the pages fed to it are section/index pages whose `<h1>` is the section name.
- The defect is upstream in `discover_listing` (wrong URLs), not in `parse_article` itself.
