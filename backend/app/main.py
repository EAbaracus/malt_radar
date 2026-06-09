import os
import re
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Query

from app.models.schemas import WhiskySearchItem, WhiskyPriceItem, NormalizeRequest
from app.providers.base import WhiskyProvider
from app.providers.csv_provider import CsvWhiskyProvider
from app.providers.mock_providers import WhiskyHunterProvider, WhiskyEditionProvider
from app.providers.distiller_provider import DistillerProvider

# Configure rate limiter (default: 60 requests per minute per IP)
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(
    title="Malt Radar API",
    description="Backend service for Malt Radar Whisky Database application",
    version="1.0.0"
)

# Attach rate limiter to app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add CORS middleware to support calls from mobile emulators or web
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize providers
providers: List[WhiskyProvider] = [
    CsvWhiskyProvider(csv_paths=["data/whisky.csv", "data/whisky2.csv", "data/whisky3.csv"]),
    # Yedek olarak mock sağlayıcıları da tutuyoruz (CSV yoksa boş dönmemesi için)
    WhiskyHunterProvider(),
    WhiskyEditionProvider(),
    DistillerProvider()
]

# Simple in-memory cache for search queries to implement the "Cache ekle" rule
search_cache = {}

# Simple API Key check from env variables
API_KEY = os.getenv("MALT_RADAR_API_KEY", "mock-secret-key-123")

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
async def search_whiskies(request: Request, q: str = ""):
    if not q or len(q.strip()) < 2:
        return []

    query = q.strip().lower()
    
    # Check cache first
    if query in search_cache:
        return search_cache[query]

    combined_results = []
    # Search all configured providers, prioritizing local CSV
    for provider in providers:
        try:
            results = provider.search(query)
            if results:
                combined_results.extend(results)
                # If we found results in the local CSV, stop to prioritize local data and save time
                if isinstance(provider, CsvWhiskyProvider):
                    break
        except Exception as e:
            # In a real app, log error but continue trying other providers
            print(f"Error from provider {provider.get_name()}: {e}")

    # Remove duplicates based on lowercased name
    unique_results = []
    seen_names = set()
    for item in combined_results:
        # Simple normalization: Lagavulin 16 and Lagavulin 16 y.o. mapped
        normalized_name = re.sub(r'\s+y\.?o\.?|\s+years?\s+old', '', item.name.lower()).strip()
        if normalized_name not in seen_names:
            seen_names.add(normalized_name)
            unique_results.append(item)

    # Save to simple cache
    search_cache[query] = unique_results
    return unique_results

@app.get("/api/whiskies/{external_id}", response_model=WhiskySearchItem)
@limiter.limit("60/minute")
async def get_whisky_details(request: Request, external_id: str):
    # Determine provider by prefix
    target_provider = None
    if external_id.startswith("csv-"):
        target_provider = providers[0]  # CsvWhiskyProvider
    elif external_id.startswith("wh-"):
        target_provider = providers[1]  # WhiskyHunter
    elif external_id.startswith("we-"):
        target_provider = providers[2]  # WhiskyEdition
    elif external_id.startswith("ds-"):
        target_provider = providers[3]  # Distiller Live
    
    if not target_provider:
        raise HTTPException(status_code=400, detail="Invalid external ID format")

    details = target_provider.get_details(external_id)
    if not details:
        raise HTTPException(status_code=404, detail="Whisky not found in external provider")
    
    return details

@app.get("/api/whiskies/{external_id}/prices", response_model=List[WhiskyPriceItem])
@limiter.limit("60/minute")
async def get_whisky_prices(request: Request, external_id: str):
    target_provider = None
    if external_id.startswith("csv-"):
        target_provider = providers[0]
    elif external_id.startswith("wh-"):
        target_provider = providers[1]
    elif external_id.startswith("we-"):
        target_provider = providers[2]
    elif external_id.startswith("ds-"):
        target_provider = providers[3]

    if not target_provider:
        raise HTTPException(status_code=400, detail="Invalid external ID format")

    prices = target_provider.get_prices(external_id)
    return prices

@app.post("/api/whiskies/normalize")
@limiter.limit("15/minute")
async def normalize_whisky_name(request: Request, req: NormalizeRequest):
    name = req.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name cannot be empty")
        
    # Apply casing rules and cleanup expressions like "y.o." or "Years old"
    normalized = name.title()
    normalized = re.sub(r'(?i)\s+y\.?o\.?$', ' Year Old', normalized)
    normalized = re.sub(r'(?i)\s+years?\s+old$', ' Year Old', normalized)
    
    # Clean multiple spaces
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    
    return {
        "original": name,
        "normalized": normalized
    }
