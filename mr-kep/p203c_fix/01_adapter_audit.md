# P203C-FIX — 01 Adapter Discovery Audit

## Method
Each adapter's `discover_listing()` inspected: URL extraction, selector, pagination, filtering, dedup.

## Per-source

| source | current selector | failure mode | required change | fixture |
|---|---|---|---|---|
| thewhiskyphiles | `discover_listing: pattern /20\d\d/\d\d/` | called on site ROOT (not /category/tasting-notes/); root had no YYYY/MM links; fallback grabbed section pages; listing URL itself 404 | use start_urls[0] (/category/tasting-notes/); hardened _discover_articles excludes cat/tag/author/nav/self | thewhiskyphiles_real_listing.html + _real_article.html |
| whiskymonster | `discover_listing: pattern /whisky/whisky-reviews/` | listing fetch blocked HTTP 403 (WordPress.com anti-bot); 0 articles | discovery selector hardened (no selector change needed); source gated by access decision (EXCLUDE_PENDING_ACCESS) | whiskymonster_real_listing.html + _real_article.html |
| thedramble | `discover_listing: pattern /tastings/` | returned /tastings/ section pages as 'articles' (h1='Tastings'); listing self not excluded | hardened _discover_articles excludes the listing URL itself + nav/cat/tag/author | thedramble_real_listing.html + _real_article.html |
| whiskynotes_be | `discover_listing: pattern /20\d\d/` | returned section/index pages (h1='WhiskyNotes') not reviews | hardened discovery excludes nav/cat/tag/author/self; only year-path permalinks kept | whiskynotes_be_real_listing.html + _real_article.html |
| thewhiskeywash | `discover_listing: pattern /whiskey-reviews/` | returned sub-category pages (h1='Whiskey Reviews','American WhiskeyReviews'...) | hardened discovery excludes listing self + nav/cat/tag/author; keeps /whiskey-reviews/<slug>/ | thewhiskeywash_real_listing.html + _real_article.html |
| wordsofwhisky | `discover_listing: pattern /20\d\d/` | 0 article URLs from homepage (landing page, not blog index) | hardened discovery kept; real entry point needs verification (root may be landing, not blog). Flagged remaining. | wordsofwhisky_real_listing.html + _real_article.html |

## Shared fix
- Added `_discover_articles(html, listing_url, include, cap)` + `_EXCLUDE_RE` (cat/tag/author/nav/feed/asset).
- All six adapters now call `_discover_articles` with their positive `include` pattern; the listing URL itself and non-article URLs are excluded.
- Deterministic, deduped, capped (no pagination expansion, no search, no archive).

## Remaining
- `wordsofwhisky` real blog entry point unverified (homepage may be a landing page). Selector is correct for year-path articles; needs a verified listing URL before live run.
- `whiskymonster` gated by access decision (see 08).
