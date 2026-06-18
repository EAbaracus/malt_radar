from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, List, Dict, Any
import os
import sqlite3
from app.services.db_read_service import DbReadService



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
def get_health(service: DbReadService = Depends(get_service)):
    try:
        return service.get_health()
    except Exception as e:
        raise HTTPException(status_code=503, detail="Database connection failed")

@router.get("/whiskies")
def get_whiskies(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    q: Optional[str] = Query(None),
    distillery_id: Optional[str] = Query(None),
    service: DbReadService = Depends(get_service)
):
    try:
        return service.get_whiskies(limit, offset, q, distillery_id)
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Database file missing")
    except sqlite3.Error:
        raise HTTPException(status_code=500, detail="Database query failed")

@router.get("/whiskies/{whisky_id}")
def get_whisky(whisky_id: str, service: DbReadService = Depends(get_service)):
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
def get_distilleries(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service: DbReadService = Depends(get_service)
):
    try:
        return service.get_distilleries(limit, offset)
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Database file missing")
    except sqlite3.Error:
        raise HTTPException(status_code=500, detail="Database query failed")

@router.get("/search")
def search(q: str = Query(...), service: DbReadService = Depends(get_service)):
    if not q or len(q.strip()) < 2:
        raise HTTPException(status_code=400, detail="Search query must be at least 2 characters")
    try:
        return service.search(q)
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Database file missing")
    except sqlite3.Error:
        raise HTTPException(status_code=500, detail="Database query failed")

@router.get("/filters")
def get_filters(service: DbReadService = Depends(get_service)):
    try:
        return service.get_filters()
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Database file missing")
    except sqlite3.Error:
        raise HTTPException(status_code=500, detail="Database query failed")

@router.get("/whiskies/{id}/flavor-profile")
def get_flavor_profile(id: str, service: DbReadService = Depends(get_service)):
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
def get_tasting_notes(id: str, service: DbReadService = Depends(get_service)):
    try:
        return service.get_tasting_notes(id)
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Database file missing")
    except sqlite3.Error:
        raise HTTPException(status_code=500, detail="Database query failed")

@router.get("/whiskies/{id}/price-history")
def get_price_history(id: str, service: DbReadService = Depends(get_service)):
    try:
        return service.get_price_history(id)
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Database file missing")
    except sqlite3.Error:
        raise HTTPException(status_code=500, detail="Database query failed")
