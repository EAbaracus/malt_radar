# Deploy live status (GCP e2-micro · 34.60.144.38)

Status: **Backend-only "internal" mode — webapp/catalog intentionally NOT public.**

## Decision (2026-08-07)
Per user: keep the webapp + catalog **internal** for now. The domain is
acquired (`maltradar.com`, Cloudflare Registrar) but **on hold** until the
`/api/db` per-user gating is landed. Current exposed surface = backend health +
auth only; catalogue stays off.

## Verified live facts (checked over SSH, `trblnfxn@34.60.144.38`)

| Component | State | Evidence |
|-----------|-------|----------|
| SSH | ✅ | `~/.ssh/mr_deploy` key; user `trblnfxn` (short OS-Login) |
| Docker / Compose | ✅ | 26.1.5 / 2.26.1-4 |
| Repo | ✅ /srv/maltradar | deploy/ backend/ frontend/ |
| production.db | ✅ RO copy | `MALT_RADAR_DB_PATH=/srv/data/production.db` |
| Backend api container | ✅ Up | `deploy-api-1` Up 5h; health **200** (in-container) |
| Catalog `/api/db` | 🔒 OFF | `DB_API_ENABLED=false`; no-key → **403** |
| Caddy | ❌ not up | no caddy container → no 80/443 |
| External surface | 🔒 SSH only | 22 OPEN; 80/443 refused; 8080 unpublished |

## Anti-scrape precondition (before public webapp)
`/api/db` must be migrated to per-user bearer auth before `DB_API_ENABLED=true`
for a public webapp; a shared API key must never ship to a browser. Until then
the catalogue stays off (current state is the safe state).

## Next (deferred, in order)
1. `/api/db` per-user gating (anti-scrape prerequisite).
2. Web build → `deploy/web-build/` + Caddy up + DNS A record + `https://maltradar.com`.

## Catalog sources (updated 2026-08-07)
- `/api/db` → `backend/data` (gated off for public web; `DB_API_ENABLED=false`).
- `/api/whiskies/search` → **CSV-only single source** (`CsvWhiskyProvider`).
- Mock (`WhiskyHunterProvider`, `WhiskyEditionProvider`) + external `DistillerProvider`
  (distiller.com scraper) **removed** (`49a5ed24`). No third-party scraped data surface.
- `deploy/.env.example` now defaults `DB_API_ENABLED=false` (was `true`) — safe default
  until per-user bearer auth lands.
