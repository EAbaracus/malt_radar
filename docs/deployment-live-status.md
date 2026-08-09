# Deploy live status (GCP e2-micro · 34.60.144.38)

Status: **Backend "internal" mode — webapp/catalog not yet public** (waits on
the human provisioning step; the anti-scrape *code* prerequisite is done).

## Anti-scrape prerequisite — RESOLVED (2026-08-09)

`/api/db` is now gated by **per-user bearer auth** (`get_current_user`, commit
`68bb9b4`) — the shared `MALT_RADAR_API_KEY` no longer guards catalog reads and
is not depended on by any browser client. The anti-scrape precondition
("migrate /api/db to per-user bearer before `DB_API_ENABLED=true` for a public
webapp") is **met**. Verified: `test_db_read_api_smoke` + `test_db_adapter_hardening`
+ `test_security_authz` → **30 passed, 1 skipped**.

It is now safe to set `DB_API_ENABLED=true` for a public webapp.

## Live facts (verified over SSH, `trblnfxn@34.60.144.38`)

| Component | State | Evidence |
|-----------|-------|----------|
| SSH | ✅ | `~/.ssh/mr_deploy` key; user `trblnfxn` |
| Docker / Compose | ✅ | 26.1.5 / 2.26.1-4 |
| Repo | ✅ /srv/maltradar | deploy/ backend/ frontend/ |
| production.db | ✅ RO copy | `MALT_RADAR_DB_PATH=/srv/data/production.db` |
| Backend api container | ✅ Up | `deploy-api-1` health 200 (in-container) |
| Catalog `/api/db` | 🔒 OFF (default) | `DB_API_ENABLED=false` → 403; NOW auth-gated |
| Caddy | ❌ not up | no 80/443 yet (human step remains) |
| External surface | 🔒 SSH only | 22 OPEN; 80/443 refused; 8080 unpublished |

## Next (in order) — human provision steps

1. Build web: `cd frontend && flutter build web --dart-define=MALT_RADAR_API_BASE_URL=https://maltradar.com`
   → copy `frontend/build/web/*` to `deploy/web-build/`. Verify no catalog CSV:
   `find build/web -name "*.csv"` empty.
2. `cd deploy && cp .env.example .env` → `MALT_RADAR_API_KEY=$(openssl rand -hex 32)`,
   `DB_API_ENABLED=true`.
3. DNS A record `maltradar.com` → VM public IP.
4. `docker compose up -d` + Caddy validate (per `deploy/README` verify step).
5. Verify: `curl https://maltradar.com/api/health`, `/` loads, `/robots.txt`
   `Disallow: /api/`, same-origin no CORS.

## Catalog sources (updated 2026-08-09)
- `/api/db` → `production.db` (per-user bearer gated; the only catalog surface).
- `/api/whiskies/*` **closed** (`b6880bb`) — legacy CSV provider routes removed;
  `CsvWhiskyProvider` deleted. Catalog reads are `/api/db` only.
- `deploy/.env.example` defaults `DB_API_ENABLED=false` (safe default); now safe
  to flip true for public web post-provision.
