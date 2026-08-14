# Malt Radar — Deploy (free tier, single-box)

Hosts the static Flutter web app and the FastAPI backend on ONE free-tier VM
behind Caddy (auto TLS, same-origin → no CORS).

Cost: **server $0** (GCP e2-micro Always Free) · **domain ~$10–15/yr** (only
recurring cost).

```
[FastAPI + SQLite]  users.db (rw) + production.db (read-only copy)
        ^ :8080
   [Caddy]  <--static Flutter web (/),  reverse-proxy /api/* -->
        ^  :443  (Let's Encrypt auto)
   https://maltradar.com
```

## Directory layout

```
deploy/
  Dockerfile              # uvicorn image (single worker for SQLite)
  Caddyfile               # TLS + static web + /api reverse proxy
  docker-compose.yml      # api + caddy
  systemd/…service        # non-docker alternative
  .env.example            # env template (copy -> .env, never commit)
  data/                   # production.db (ro) + users.db (rw)
  web-build/              # flutter build web output
```

## Anti-scrape prerequisite (resolved)

`/api/db` is now gated by **per-user bearer auth** (`get_current_user`) — not a
shared key (commit 68bb9b4). A public webapp authenticates with the account
token; `MALT_RADAR_API_KEY` never ships to a browser, preserving the
anti-scrape posture. It is therefore now safe to set `DB_API_ENABLED=true` for
a public webapp. Keep the shared key out of the Flutter web bundle; forbidding
it server-side is handled by the bearer dependency.

## Rate limiting (audit, 2026-08-10)

- **Configured:** SlowAPI `@limiter.limit("120/minute")` per `/api/db`
  endpoint, `Limiter(key_func=get_remote_address)`, in-memory storage (single
  uvicorn worker → consistent). `app/security.py:16`.
- **Effective ceiling:** live probing shows ~25–30 requests/min before 429
  (130 requests → 24×200 + 106×429). Headers: `Server: cloudflare`,
  `CF-RAY`, `cf-cache-status: DYNAMIC`, `via: 1.1 Caddy`. The backend emits
  no rate-limit headers on 200 (SlowAPI `Retry-After` only appears on 429).
- **Suspected source of the ~25–30 ceiling:** a **Cloudflare edge rate-limit
  rule** (dashboard-level, not visible in headers). Caddy has no rate limit
  (see `deploy/Caddyfile`). Verify in the CF dashboard before changing the
  SlowAPI config — do NOT raise the app limit to "match" the observed
  ceiling without confirming where it comes from.
- **Client contract:** the Flutter catalog is human-paced (one page-50
  request per scroll, `CatalogPaginationNotifier`) and must never eager-fetch
  the whole catalog (the old 100-page cascade 429'd into an empty list — the
  H1 hardening removed it).

## Catalog pagination contract (H4, 2026-08-10)

- Server: `CATALOG_MAX_PAGE=50` (clamped, `limit` max 100 rejected),
  `CATALOG_MAX_OFFSET=10000` (`CatalogBoundsError` → 400). Anti-scrape bounds.
- Client: paginated state fetches page-by-page (50) and stops on a short
  page; 429/error marks `temporarilyUnavailable` — existing items stay
  visible, no retry storm.
- The 5000-row client headroom (never reached now — `hasMore` stops early)
  vs the 10000-row server guard is a **deliberate safe-direction gap**: the
  client can never hit the server offset guard first. `getSimilarWhiskies`
  uses a bounded 5-page fetch (250 rows) for the same reason.
- All of the above is bearer-gated; unauthenticated requests are refused by
  the auth dependency **before** the service/DB layer (abuse surface closed).

## Provisioning checklist (human steps — GCP account is yours to create)

1. **GCP Cloud Free Tier** → sign up:
   - Compute Engine → Create VM → Machine type **e2-micro** (x86, 1 vCPU /
     1 GB RAM, Always Free).
   - Boot volume ≥ 30 GB (free quota); mount at `/srv/maltradar`.
   - Image: **Ubuntu 22.04/24.04 LTS**; firewall rules open **22, 80, 443**.
   - Save the SSH key (`~/.ssh/mr_deploy`).
2. **Install** on the box: `apt-get install -y docker.io docker-compose-plugin` (or
   Caddy directly + systemd unit).
3. **Copy repo** to the box (or `git clone` your `malt_radar` repo).
4. **Domain → DNS:** point `maltradar.com` (A record) to the VM's public IP.
   Edit `deploy/Caddyfile` + `.env` `MALT_RADAR_ALLOWED_ORIGINS` to your domain.
5. **Data:** copy a read-only `production.db` snapshot into `deploy/data/`
   (chmod 444; it is never written on the host — PromotionGate stays local/CI).
6. **Web build:** `cd frontend && flutter build web \
   --dart-define=MALT_RADAR_API_BASE_URL=https://maltradar.com \
   --dart-define=GOOGLE_CLIENT_ID_WEB=<same id as .env GOOGLE_CLIENT_ID>` then copy
   `frontend/build/web/*` → `deploy/web-build/`.
   - **Google Sign-In:** the web client id must be identical in the build
     (`GOOGLE_CLIENT_ID_WEB`) and in `.env` (`GOOGLE_CLIENT_ID`) — the backend
     uses it as the id_token audience; a mismatch yields 401 on /api/auth/google.
     Add the app origin (`https://maltradar.com`) to the client's Authorized
     JavaScript origins in Google Cloud Console.
   - **Catalog CSV is already absent from the client** (removed at source —
     see `docs/ads-monetization.md` / anti-scrape work): the catalog CSVs are no
     longer bundled in any client target. Before publishing, verify the web
     bundle carries no catalog payload: `find build/web -name "*.csv"` must be
     empty (see the nodata probe in the deployment workflow).
7. **Env:** `cp deploy/.env.example deploy/.env` and fill `MALT_RADAR_API_KEY`
   (`openssl rand -hex 32`) + domain.
8. **Run:** `cd deploy && docker compose up -d`.
9. **Verify:**
   - `curl -k https://maltradar.com/api/health` → `{"status":"healthy",...}`
   - Browser loads `/` (webapp), `/api` works same-origin, no CORS error.
   - `curl https://maltradar.com/robots.txt` → `Disallow: /api/`.

## Backup (SQLite)

- `users.db` is the writable store: daily backup + SHA256 to cloud/object
  storage, independently of `production.db` (which is immutable/CI-managed).
- Login via account is required for catalogue reads once per-user auth lands.

## Alternatives (not recommended)

- Render/Railway free web tiers: **ephemeral disk** → SQLite data is lost on
  restart. No.
- Vercel/Cloudflare Workers: serverless, no persistent SQLite writes → requires
  a DB rewrite. Only if you want to drop the VM (expensive rewrite).
