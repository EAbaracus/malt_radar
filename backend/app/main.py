import os
import re
from fastapi import FastAPI, HTTPException, Request, Response, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from typing import List, Optional
from slowapi.errors import RateLimitExceeded
import collections

from app.security import limiter, verify_api_key, API_KEY_HEADER
from app.security import _rate_limit_exceeded_handler
from app.models.schemas import WhiskySearchItem, WhiskyPriceItem, NormalizeRequest
from app.providers.base import WhiskyProvider
from app.providers.csv_provider import CsvWhiskyProvider
from app.providers.mock_providers import WhiskyHunterProvider, WhiskyEditionProvider
from app.providers.distiller_provider import DistillerProvider
from app.routers import admin_review
from app.routers import db_api

app = FastAPI(
    title="Malt Radar API",
    description="Backend service for Malt Radar Whisky Database application",
    version="1.0.0"
)

# Attach rate limiter to app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Include Admin Review router (protected by feature flag logic inside the router)
app.include_router(admin_review.router)

# Include new Read-Only DB API router
app.include_router(db_api.router)

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

# Initialize providers
provider_instances = [
    CsvWhiskyProvider(csv_paths=["data/whisky_database_merged_max.csv"]),
    WhiskyHunterProvider(),
    WhiskyEditionProvider(),
    DistillerProvider()
]

# Robust provider mapping
provider_map = {
    "csv": provider_instances[0],
    "wh": provider_instances[1],
    "we": provider_instances[2],
    "ds": provider_instances[3]
}

# Bounded LRU cache (max 256 items)
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

@app.get("/api/whiskies/search", response_model=List[WhiskySearchItem])
@limiter.limit("120/minute")
async def search_whiskies(request: Request, q: str = "", api_key: str = Depends(verify_api_key)):
    if not q or len(q.strip()) < 2:
        return []

    query = q.strip().lower()
    
    # Check cache first
    cached_result = search_cache.get(query)
    if cached_result is not None:
        return cached_result

    combined_results = []
    # Search all configured providers, prioritizing local CSV
    for provider in provider_instances:
        try:
            results = provider.search(query)
            if results:
                combined_results.extend(results)
                if isinstance(provider, CsvWhiskyProvider):
                    break
        except Exception as e:
            print(f"Error from provider {provider.get_name()}: {e}")

    # Remove duplicates based on lowercased name
    unique_results = []
    seen_names = set()
    for item in combined_results:
        normalized_name = re.sub(r'\s+y\.?o\.?|\s+years?\s+old', '', item.name.lower()).strip()
        if normalized_name not in seen_names:
            seen_names.add(normalized_name)
            unique_results.append(item)

    # Save to cache
    search_cache.put(query, unique_results)
    return unique_results

def get_provider(external_id: str):
    prefix = external_id.split("-")[0] if "-" in external_id else ""
    return provider_map.get(prefix)

@app.get("/api/whiskies/{external_id}", response_model=WhiskySearchItem)
@limiter.limit("60/minute")
async def get_whisky_details(request: Request, external_id: str, api_key: str = Depends(verify_api_key)):
    target_provider = get_provider(external_id)
    if not target_provider:
        raise HTTPException(status_code=400, detail="Invalid external ID format")

    details = target_provider.get_details(external_id)
    if not details:
        raise HTTPException(status_code=404, detail="Whisky not found in external provider")
    
    return details

@app.get("/api/whiskies/{external_id}/prices", response_model=List[WhiskyPriceItem])
@limiter.limit("60/minute")
async def get_whisky_prices(request: Request, external_id: str, api_key: str = Depends(verify_api_key)):
    if os.getenv("SHOW_PRICE_DATA", "false").lower() != "true":
        return []
        
    target_provider = get_provider(external_id)
    if not target_provider:
        raise HTTPException(status_code=400, detail="Invalid external ID format")

    prices = target_provider.get_prices(external_id)
    return prices

@app.post("/api/whiskies/normalize")
@limiter.limit("15/minute")
async def normalize_whisky_name(request: Request, req: NormalizeRequest, api_key: str = Depends(verify_api_key)):
    name = req.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name cannot be empty")
        
    normalized = name
    
    # Clean expressions like "y.o." or "Years old" without regex to prevent ReDoS
    lower_norm = normalized.lower()
    for suffix in [" y.o.", " y.o", " yo.", " yo", " year old", " years old"]:
        if lower_norm.endswith(suffix):
            normalized = normalized[:-len(suffix)].strip() + " Year Old"
            break
    
    # Avoid blanket .title() to preserve special words
    preserve_list = ['IPA', 'NAS', 'PX', 'CS', 'XO', 'VSOP', 'OFC']
    words = normalized.split()
    new_words = []
    for w in words:
        if w.upper() in preserve_list:
            new_words.append(w.upper())
        else:
            # Simple capitalize, keeping internal casing intact if possible
            if len(w) > 0:
                new_words.append(w[0].upper() + w[1:])
    
    normalized = " ".join(new_words)
    
    # Clean multiple spaces
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    
    return {
        "original": name,
        "normalized": normalized
    }
