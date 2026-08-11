import os
import collections
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi.errors import RateLimitExceeded

from app.security import limiter, verify_api_key, API_KEY_HEADER
from app.security import _rate_limit_exceeded_handler
from app.routers import admin_review
from app.routers import db_api
from app.auth.routes import router as auth_router

app = FastAPI(
    title="Malt Radar API",
    description="Backend service for Malt Radar Whisky Database application",
    version="1.0.0"
)

# Attach rate limiter to app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# OAuth verifier DI hook: defaults to None -> routes fall back to the
# provider registry (GoogleIdentityVerifier). Tests override with a fake.
app.state.google_verifier = None

# Include Admin Review router (protected by feature flag logic inside the router)
app.include_router(admin_review.router)

# Include new Read-Only DB API router (per-user bearer-authenticated catalog)
app.include_router(db_api.router)

# Include auth + per-user sync router (separate from the whisky production DB)
app.include_router(auth_router)

# Fix CORS: don't use * with allow_credentials=True
allowed_origins_env = os.getenv("MALT_RADAR_ALLOWED_ORIGINS", "")
if allowed_origins_env:
    allowed_origins = [o.strip() for o in allowed_origins_env.split(",")]
else:
    allowed_origins = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
        "http://localhost:8888",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False if "*" in allowed_origins else True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Security headers middleware (P1 hardening, scope 2026-08-06)
#
# Applies hardcoded defense-in-depth response headers to EVERY response,
# including error responses. Header values are fixed and safe for a
# JSON-only API surface; they are NOT derived from request input, so this
# introduces no reflection/CSP-bypass vector.
#
# HSTS note: only meaningful when served over HTTPS. The value is still set
# unconditionally so the header is present behind whatever TLS terminator /
# proxy terminates HTTPS; the deployment's TLS termination point must be
# verified separately at deployment time.
# ---------------------------------------------------------------------------
SECURITY_HEADERS = {
    # max-age=1y, includeSubDomains; preload flag omitted (needs domain consent)
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    # JSON-only API: deny all non-API resource loads by default
    "Content-Security-Policy": "default-src 'none'",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    # Database/search API responses are not cacheable
    "Cache-Control": "no-store",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        for name, value in SECURITY_HEADERS.items():
            response.headers[name] = value
        return response


app.add_middleware(SecurityHeadersMiddleware)

# Bounded LRU cache (max 256 items) — kept for /api/health telemetry parity;
# the CSV-provider search cache path was removed with /api/whiskies/* closure.
class LRUCache:
    def __init__(self, capacity: int):
        self.cache = collections.OrderedDict()
        self.capacity = capacity

    def get(self, key):
        if key not in self.cache:
            return None
        self.cache.move_to_end(key)
        return self.cache[key]

    def put(self, key, value):
        self.cache[key] = value
        self.cache.move_to_end(key)
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)

    def __len__(self):
        return len(self.cache)


search_cache = LRUCache(256)

# Security: Require API key for public endpoints
# Backwards-compatible re-export: tests and routers may still import
# verify_api_key / API_KEY_HEADER via app.main.
verify_api_key = verify_api_key
API_KEY_HEADER = API_KEY_HEADER

@app.get("/api/health")
@limiter.limit("10/minute")
async def health_check(request: Request):
    return {
        "status": "healthy",
        "version": "1.0.0",
        "cached_queries_count": len(search_cache)
    }
