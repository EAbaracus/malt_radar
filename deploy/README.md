# Malt Radar — Deploy (free tier, single-box)

Hosts the static Flutter web app and the FastAPI backend on ONE free-tier VM
behind Caddy (auto TLS, same-origin → no CORS).

Cost: **server $0** (Oracle Cloud Always Free) · **domain ~$10–15/yr** (only
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

## Anti-scrape prerequisite (READ FIRST)

The public webapp reads the catalog through `/api/db`. Today:

- `/api/db` is gated by the **shared** `MALT_RADAR_API_KEY` header.
- `DbWhiskyApiClient` (frontend) does **not** send that header → DbApi-mode web
  calls currently 403.

**Before enabling `DB_API_ENABLED=true` for a public webapp** you must either:

1. **Migrate `/api/db` to per-user bearer auth** (recommended; reuse
   `backend/app/auth` token check) so the client authenticates with the account
   token — the shared key never ships to browsers, preserving the anti-scrape
   posture; **or**
2. Inject the key server-side for same-origin only (Caddy cannot do this
   cleanly; a trust boundary change). Do **not** embed `MALT_RADAR_API_KEY` in
   the Flutter web bundle — a scraper reads it.

Until then, keep `DB_API_ENABLED=false` for the public webapp (local/dev and
non-web clients can keep it on with the key).

## Provisioning checklist (human steps — Oracle account is yours to create)

1. **Oracle Cloud Free** → sign up (Ampere A1):
   - Compute → Create instance → Shape: **VM.Standard.A1.Flex** (ARM),
     OCPU **4**, RAM **24 GB**.
   - Boot volume: keep ≥ **100 GB** (free quota), or attach a **block volume**
     (200 GB free) mounted at `/srv/maltradar`.
   - Image: **Ubuntu 22.04/24.04 LTS**; open security list ports **22, 80, 443**.
   - Save the SSH key.
2. **Install** on the box: `apt-get install -y docker.io docker-compose-plugin` (or
   Caddy directly + systemd unit).
3. **Copy repo** to the box (or `git clone` your `malt_radar` repo).
4. **Domain → DNS:** point `maltradar.com` (A record) to the VM's public IP.
   Edit `deploy/Caddyfile` + `.env` `MALT_RADAR_ALLOWED_ORIGINS` to your domain.
5. **Data:** copy a read-only `production.db` snapshot into `deploy/data/`
   (chmod 444; it is never written on the host — PromotionGate stays local/CI).
6. **Web build:** `cd frontend && flutter build web \
   --dart-define=MALT_RADAR_API_BASE_URL=https://maltradar.com` then copy
   `frontend/build/web/*` → `deploy/web-build/`.
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
