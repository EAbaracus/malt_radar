from fastapi import APIRouter, HTTPException, Query, Depends, Request
from typing import Optional, List, Dict, Any
import os
import sqlite3
from app.services.db_read_service import DbReadService, CatalogBoundsError
from app.security import limiter
from app.auth.routes import get_current_user



def check_db_api_enabled():
    if os.getenv("DB_API_ENABLED", "false").lower() != "true":
        raise HTTPException(status_code=403, detail="DB API is disabled")

router = APIRouter(
    prefix="/api/db", 
    tags=["DB API Adapter"],
    dependencies=[Depends(check_db_api_enabled)]
)

def get_service() -> DbReadService:
    return DbReadService()

@router.get("/health")
@limiter.limit("60/minute")
def get_health(request: Request, service: DbReadService = Depends(get_service)):
    try:
        return service.get_health()
    except Exception as e:
        raise HTTPException(status_code=503, detail="Database connection failed")

@router.get("/whiskies")
@limiter.limit("120/minute")
def get_whiskies(
    request: Request,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    q: Optional[str] = Query(None),
    distillery_id: Optional[str] = Query(None),
    service: DbReadService = Depends(get_service)
):
    try:
        return service.get_whiskies(limit, offset, q, distillery_id)
    except CatalogBoundsError:
        raise HTTPException(status_code=400, detail="Offset beyond catalog browse limit")
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Database file missing")
    except sqlite3.Error:
        raise HTTPException(status_code=500, detail="Database query failed")

@router.get("/whiskies/{whisky_id}")
@limiter.limit("120/minute")
def get_whisky(request: Request, whisky_id: str, service: DbReadService = Depends(get_service)):
    try:
        result = service.get_whisky(whisky_id)
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Database file missing")
    except sqlite3.Error:
        raise HTTPException(status_code=500, detail="Database query failed")
        
    if not result:
        raise HTTPException(status_code=404, detail="Whisky not found")
    return result

@router.get("/distilleries")
@limiter.limit("120/minute")
def get_distilleries(
    request: Request,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service: DbReadService = Depends(get_service)
):
    try:
        return service.get_distilleries(limit, offset)
    except CatalogBoundsError:
        raise HTTPException(status_code=400, detail="Offset beyond catalog browse limit")
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Database file missing")
    except sqlite3.Error:
        raise HTTPException(status_code=500, detail="Database query failed")

@router.get("/search")
@limiter.limit("120/minute")
def search(request: Request, q: str = Query(...), service: DbReadService = Depends(get_service)):
    if not q or len(q.strip()) < 2:
        raise HTTPException(status_code=400, detail="Search query must be at least 2 characters")
    try:
        return service.search(q)
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Database file missing")
    except sqlite3.Error:
        raise HTTPException(status_code=500, detail="Database query failed")

@router.get("/filters")
@limiter.limit("120/minute")
def get_filters(request: Request, service: DbReadService = Depends(get_service)):
    try:
        return service.get_filters()
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Database file missing")
    except sqlite3.Error:
        raise HTTPException(status_code=500, detail="Database query failed")

@router.get("/whiskies/{id}/flavor-profile")
@limiter.limit("120/minute")
def get_flavor_profile(request: Request, id: str, service: DbReadService = Depends(get_service)):
    try:
        result = service.get_flavor_profile(id)
        if not result:
            raise HTTPException(status_code=404, detail="Flavor profile not found")
        return result
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Database file missing")
    except sqlite3.Error:
        raise HTTPException(status_code=500, detail="Database query failed")

@router.get("/whiskies/{id}/tasting-notes")
@limiter.limit("120/minute")
def get_tasting_notes(request: Request, id: str, service: DbReadService = Depends(get_service)):
    try:
        return service.get_tasting_notes(id)
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Database file missing")
    except sqlite3.Error:
        raise HTTPException(status_code=500, detail="Database query failed")

@router.get("/whiskies/{id}/evidence")
@limiter.limit("120/minute")
def get_evidence(request: Request, id: str, service: DbReadService = Depends(get_service)):
    """Return official_source_references for a whisky exactly as stored (read-only)."""
    try:
        return service.get_official_source_references(id)
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Database file missing")
    except sqlite3.Error:
        raise HTTPException(status_code=500, detail="Database query failed")

@router.get("/whiskies/{id}/price-history")
@limiter.limit("120/minute")
def get_price_history(request: Request, id: str, service: DbReadService = Depends(get_service)):
    if os.getenv("SHOW_PRICE_DATA", "false").lower() != "true":
        return []
    try:
        return service.get_price_history(id)
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Database file missing")
    except sqlite3.Error:
        raise HTTPException(status_code=500, detail="Database query failed")
