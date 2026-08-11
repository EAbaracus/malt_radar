from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional
import os
from app.providers.sqlite_read_adapter import SqliteReadAdapter

router = APIRouter(prefix="/api/db", tags=["Database Read-Only API"])

def check_api_enabled():
    if os.getenv("DB_API_ENABLED", "true").lower() != "true":
        raise HTTPException(status_code=404, detail="DB API is disabled")

router.dependencies = [Depends(check_api_enabled)]

def get_adapter() -> SqliteReadAdapter:
    return SqliteReadAdapter()

@router.get("/health")
def health_check(adapter: SqliteReadAdapter = Depends(get_adapter)):
    return adapter.get_health()

@router.get("/schema")
def get_schema(adapter: SqliteReadAdapter = Depends(get_adapter)):
    return adapter.get_schema()

@router.get("/whiskies")
def get_whiskies(
    limit: int = Query(50, ge=1), 
    offset: int = Query(0, ge=0),
    q: Optional[str] = Query(None),
    adapter: SqliteReadAdapter = Depends(get_adapter)
):
    return adapter.get_whiskies(limit, offset, q)

@router.get("/whiskies/{id}")
def get_whisky(id: str, adapter: SqliteReadAdapter = Depends(get_adapter)):
    result = adapter.get_whisky(id)
    if not result:
        raise HTTPException(status_code=404, detail="Whisky not found")
    return result

@router.get("/distilleries")
def get_distilleries(
    limit: int = Query(50, ge=1), 
    offset: int = Query(0, ge=0),
    q: Optional[str] = Query(None),
    adapter: SqliteReadAdapter = Depends(get_adapter)
):
    return adapter.get_distilleries(limit, offset, q)

@router.get("/distilleries/{id}")
def get_distillery(id: str, adapter: SqliteReadAdapter = Depends(get_adapter)):
    result = adapter.get_distillery(id)
    if not result:
        raise HTTPException(status_code=404, detail="Distillery not found")
    return result

@router.get("/whiskies/{id}/flavor-profile")
def get_flavor_profile(id: str, adapter: SqliteReadAdapter = Depends(get_adapter)):
    # Returns null/empty dict or 404, as implemented in adapter it returns None if not found
    result = adapter.get_flavor_profile(id)
    if not result:
        raise HTTPException(status_code=404, detail="Flavor profile not found")
    return result

@router.get("/whiskies/{id}/tasting-notes")
def get_tasting_notes(id: str, adapter: SqliteReadAdapter = Depends(get_adapter)):
    # Returns empty list if not found
    return adapter.get_tasting_notes(id)

@router.get("/whiskies/{id}/price-history")
def get_price_history(id: str, adapter: SqliteReadAdapter = Depends(get_adapter)):
    if os.getenv("SHOW_PRICE_DATA", "false").lower() != "true":
        return []
    # Returns empty list if not found
    return adapter.get_price_history(id)
