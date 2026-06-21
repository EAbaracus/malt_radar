# 295 Real Tasting Note Acquisition Strategy Report

## Evaluated Strategies

### Manual curated URL/file import
- **feasibility**: High
- **legal_risk**: Low (requires fair use review of sources)
- **data_quality_risk**: Low (human vetted)
- **engineering_effort**: Low (pipeline already exists for uploaded_document/manual CSV)
- **expected_yield**: Low-Medium (time intensive)
- **cost**: Free
- **recommendation**: Recommended as baseline
- **next_phase**: Prepare template CSV for manual note collection

### Playwright/Selenium browser fetch
- **feasibility**: Medium
- **legal_risk**: Medium (must respect robots.txt and Terms of Service)
- **data_quality_risk**: Medium (requires DOM parsing per site)
- **engineering_effort**: High
- **expected_yield**: Medium-High
- **cost**: Free
- **recommendation**: Not recommended (high maintenance, potential ToS violations)
- **next_phase**: N/A

### Scraping API services (ScrapingBee, ZenRows)
- **feasibility**: High
- **legal_risk**: Medium (outsources fetch but underlying legal/ToS risks persist)
- **data_quality_risk**: Medium
- **engineering_effort**: Medium
- **expected_yield**: High
- **cost**: Paid ($$)
- **recommendation**: Not recommended (costly, anti-bot bypass is discouraged)
- **next_phase**: N/A

### Source Exchange (API / RSS / Sitemap / Static HTML)
- **feasibility**: Medium
- **legal_risk**: Low (using publicly provided developer endpoints or feeds)
- **data_quality_risk**: Low
- **engineering_effort**: Medium
- **expected_yield**: Medium
- **cost**: Free / Freemium
- **recommendation**: Highly Recommended for automation
- **next_phase**: Identify whisky DB APIs or official RSS feeds

### In-app User-generated Tasting Notes
- **feasibility**: High
- **legal_risk**: None
- **data_quality_risk**: Medium-High (requires moderation/aggregation)
- **engineering_effort**: Medium (frontend/backend feature)
- **expected_yield**: High (long-term, scales with user base)
- **cost**: Free
- **recommendation**: Highly Recommended as long-term core strategy
- **next_phase**: Design UGC schema for tasting notes

### Disable Current Web Pipeline
- **feasibility**: High
- **legal_risk**: None
- **data_quality_risk**: None
- **engineering_effort**: Low
- **expected_yield**: Zero
- **cost**: Free
- **recommendation**: Mandatory immediately
- **next_phase**: Archive discovery/fetch scripts and freeze automated pipeline

## Recommendation & Next Steps
The current automated scraping pipeline is hitting anti-bot walls. Circumventing these is discouraged. The recommended approach is a hybrid of: **Manual curated file import** (for high quality baseline) and **In-app User-generated Notes** (for scalable organic growth). The current scraping pipeline should be paused.

- production_db_changed: NO
- output_import_changed: NO
