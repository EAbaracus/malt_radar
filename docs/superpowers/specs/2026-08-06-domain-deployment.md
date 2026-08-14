# Domain Acquisition + Deployment Integration — Design

**Status:** Approved by user · **Domain:** `maltradar.com` (purchased via Cloudflare Registrar)

## Goal
Serve the Malt Radar webapp + FastAPI backend publicly at `https://maltradar.com` by wiring the purchased domain into the existing single-VM, same-origin Caddy deployment.

## Context / assumptions
- Catalog data is backend-only (no client bundle) — verified and pushed (`211abcf`..`8193353`).
- Mobile defaults to backend mode (`useDbApi=true`, `1b2ee3c`).
- Deployment is Caddy auto-TLS, same-origin `/api` (no CORS) — `deploy/Caddyfile` currently uses placeholder `maltradar.example.com`.
- `MALT_RADAR_ALLOWED_ORIGINS` is read in `backend/app/main.py:41`.
- Backend is API-key + rate-limited; `/api/db` is `DB_API_ENABLED`-gated (per-user auth is a separate, later item).

## Decision
- **TLD: `.com`** — strongest trust signal, TR + global fit, ~$10–12/yr. Chosen over `.app`/`.dev`/`.io`.
- **Registrar: Cloudflare Registrar** — at-cost pricing, no upsell, DNS on Cloudflare (edges, free, fast propagation).
- Domain **purchased** by the user (human step — credentials/ownership are theirs).

## Steps (implementation plan will detail)
1. **Point DNS:** add `maltradar.com` A record → VM public IP (Oracle free tier, Ampere A1). Cloudflare DNS.
2. **Caddyfile:** replace `maltradar.example.com` with `maltradar.com`. Caddy auto-provisions + renews Let's Encrypt for it.
3. **Env:** `deploy/.env.example` → real `.env` with:
   - `MALT_RADAR_ALLOWED_ORIGINS=https://maltradar.com`
   - fresh `MALT_RADAR_API_KEY` (`openssl rand -hex 32`)
4. **README:** update domain placeholder in the provisioning checklist.
5. **Web build:** `flutter build web --dart-define=MALT_RADAR_API_BASE_URL=https://maltradar.com` → copy `build/web/*` to `deploy/web-build/`.
6. **Deploy:** `docker compose up -d`; verify:
   - `curl -k https://maltradar.com/api/health` → healthy
   - browser loads `/`, `/api` same-origin, no CORS errors
   - `curl https://maltradar.com/robots.txt` → `Disallow: /api/`
7. **Verify nodata:** `find deploy/web-build -name "*.csv"` empty.

## Files likely to change
- `deploy/Caddyfile` (domain)
- `deploy/.env.example` (origins placeholder → domain)
- `deploy/README.md` (provisioning step 4 domain)
- (not code) `docs/ads-monetization.md` — note domain now live

## Validation
- Local: Caddy `caddy validate`-style config sanity (or rely on compose up).
- Remote after deploy: health curl + brotherbrowser check + robots.txt.
- No client bundle ships catalog data (nodata probe stays green).

## Risks / tradeoffs / open questions
- **Oracle free tier IP stability:** an ephemeral public IP breaks DNS if the VM is stopped. Mitigate with a reserved/free static IP or Cloudflare proxy (orange cloud) pointing at the current IP.
- **Shared-key gating persists:** `/api/db` still ONE `MALT_RADAR_API_KEY`; public web users will 403 unless per-user bearer auth is enabled (`DB_API_ENABLED=true`). Go-live of real user catalog reads needs the per-user auth item (README step 0) — this plan wires the domain, not the auth gate.
- **Age gate / TR compliance:** content now reachable at the public domain — age-gate already enforces pre-content; no new legal surface.
