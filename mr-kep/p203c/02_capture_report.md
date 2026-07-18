# P203C — 02 Capture Report

Sources crawled: **6** | Articles captured: **15**
Storage policy: EXCERPT_POLICY honored — NO raw HTML persisted; only URL, timestamp, headers-metadata, status, content-type, SHA256, content-length + normalized output.

## Per-source capture status

| source | listing HTTP | articles | failures | note |
|---|---|---|---|---|
| thewhiskyphiles | 404 | 0 | 0 | listing URL dead (404) |
| whiskymonster | 403 | 0 | 0 | listing fetch blocked by anti-bot (403); robots allows |
| thedramble | 200 | 5 | 0 | fetched section/index pages, not reviews |
| whiskynotes_be | 200 | 5 | 0 | fetched section/index pages, not reviews |
| thewhiskeywash | 200 | 5 | 0 | fetched section/index pages, not reviews |
| wordsofwhisky | 200 | 0 | 0 | discover_listing found 0 article URLs |

## Key finding
- **0 of 15 captured pages are actual whisky reviews.** The fetched pages are category/section landing pages (e.g. 'Tastings', 'WhiskyNotes', 'Whiskey Reviews').
- Root cause: the concrete adapters' `discover_listing` selectors do not extract real article permalinks from the live DOM. The base adapter explicitly warns: _'Actual HTML selectors per source MUST be implemented + fixture-tested before any live run.'_
- `thewhiskyphiles` listing = 404; `whiskymonster` = 403; `wordsofwhisky` = 0 URLs; the other 3 returned section pages.
- Staging rows are retained for transparency but are NOT promotion-grade.
